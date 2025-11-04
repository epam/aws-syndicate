"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import os
import shutil
from json import load
from typing import Any
from urllib.parse import urlparse

from syndicate.exceptions import ProjectStateError, \
    ResourceMetadataError, ResourceProcessingError, ParameterError, \
    InvalidValueError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import (build_py_package_name,
                                         resolve_bundle_directory)
from syndicate.core.helper import execute_command_by_path
from syndicate.core.build.validator.mapping import (VALIDATOR_BY_TYPE_MAPPING,
                                                    ALL_TYPES)
from syndicate.core.conf.processor import GLOBAL_AWS_SERVICES, \
    GLOBAL_AWS_SERVICE_PREFIXES
from syndicate.core.constants import (API_GATEWAY_TYPE, ARTIFACTS_FOLDER,
                                      BUILD_META_FILE_NAME, EBS_TYPE,
                                      LAMBDA_CONFIG_FILE_NAME, LAMBDA_TYPE,
                                      RESOURCES_FILE_NAME, RESOURCE_LIST,
                                      IAM_ROLE, LAMBDA_LAYER_TYPE,
                                      S3_PATH_NAME, APPSYNC_CONFIG_FILE_NAME,
                                      LAMBDA_LAYER_CONFIG_FILE_NAME,
                                      WEB_SOCKET_API_GATEWAY_TYPE,
                                      OAS_V3_FILE_NAME,
                                      API_GATEWAY_OAS_V3_TYPE, SWAGGER_UI_TYPE,
                                      SWAGGER_UI_CONFIG_FILE_NAME,
                                      TAGS_RESOURCE_TYPE_CONFIG)
from syndicate.core.generators.contents import FILE_POM
from syndicate.core.groups import JAVA_ROOT_DIR_JAPP, RUNTIME_JAVA
from syndicate.core.helper import (build_path, prettify_json,
                                   resolve_aliases_for_string,
                                   write_content_to_file, validate_tags)
from syndicate.core.resources.helper import resolve_dynamic_identifier, \
    detect_unresolved_aliases

DEFAULT_IAM_SUFFIX_LENGTH = 5
NAME_RESOLVING_BLACKLISTED_KEYS = [
    'prefix', 'suffix', 'resource_type', 'principal_service',
    'integration_type', 'authorization_type'
]

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def validate_deployment_packages(bundle_path, meta_resources):
    package_paths = artifact_paths(meta_resources)
    nonexistent_packages = []
    for package in package_paths:
        package_path = build_path(bundle_path, package)
        if not os.path.exists(package_path):
            nonexistent_packages.append(package_path)

    if nonexistent_packages:
        raise ProjectStateError(
            f"Bundle is not properly configured. Nonexistent deployment "
            f"packages: '{prettify_json(nonexistent_packages)}'."
        )


def artifact_paths(meta_resources):
    return [i for i in
            [_retrieve_package(v) for v in list(meta_resources.values())] if i]


def _retrieve_package(meta):
    s3_path = meta.get(S3_PATH_NAME)
    if s3_path:
        return s3_path


def _check_duplicated_resources(initial_meta_dict, additional_item_name,
                                additional_item):
    """ Match two meta dicts (overall and separated) for duplicates.

    :type initial_meta_dict: dict
    :type additional_item_name: str
    :type additional_item: dict
    """
    if additional_item_name in initial_meta_dict:
        additional_type = additional_item['resource_type']
        initial_item = initial_meta_dict[additional_item_name]
        if not initial_item:
            return
        initial_type = initial_item['resource_type']
        if additional_type == initial_type and initial_type in \
                {API_GATEWAY_TYPE, WEB_SOCKET_API_GATEWAY_TYPE}:
            _LOG.info(
                f"The API Gateway '{additional_item_name}' is defined in "
                f"different deployment resources files. Going to merge "
                f"definitions..."
            )

            # return aggregated API description
            for param_name, initial_value in initial_item.items():
                if param_name == 'resource_type':
                    continue
                elif param_name in ['api_method_responses',
                                    'api_method_integration_responses',
                                    'cluster_cache_configuration',
                                    'cluster_throttling_configuration']:
                    additional_value = additional_item.get(param_name)
                    if initial_value and additional_value:
                        raise ResourceMetadataError(
                            f"Unable to merge the API Gateway "
                            f"'{additional_item_name}' definition because "
                            f"of duplication of the parameter '{param_name}' "
                            f"in different deployment resources files. "
                            f"Please resolve the conflict."
                        )
                    if initial_value:
                        additional_item[param_name] = initial_value

                elif param_name == 'dependencies':
                    dependencies_dict = {
                        each['resource_name']: each
                        for each in additional_item.get('dependencies') or []
                    }
                    if not additional_item.get('dependencies'):
                        additional_item['dependencies'] = []
                    for each in initial_value or []:
                        if each['resource_name'] not in dependencies_dict:
                            additional_item['dependencies'].append(each)

                elif param_name in ['binary_media_types', 'apply_changes']:
                    additional_item = _merge_api_gw_list_typed_configurations(
                        initial_item,
                        additional_item,
                        [param_name],
                        additional_item_name
                    )

                elif param_name in ['authorizers', 'tags', 'models',
                                    'resources']:
                    for each in list(initial_item.get(param_name, {}).keys()):
                        if each in list(
                                additional_item.get(param_name, {}).keys()):
                            raise ResourceMetadataError(
                                f"Unable to merge the API Gateway "
                                f"'{additional_item_name}' definition due to "
                                f"duplicate '{each}' key in the "
                                f"'{param_name}' property across different "
                                f"deployment resources files. "
                                f"Please resolve the conflict."
                            )

                    initial_param_value = initial_item.get(param_name) or {}
                    additional_param_value = additional_item.get(
                        param_name) or {}
                    additional_item[param_name] = {**initial_param_value,
                                                   **additional_param_value}

                elif additional_item.get(param_name):
                    raise ResourceMetadataError(
                        f"Unable to merge the API Gateway "
                        f"'{additional_item_name}' definition due to "
                        f"duplicate of the '{param_name}' property "
                        f"across different deployment resources files. "
                        f"Please resolve the conflict."
                    )

                else:
                    additional_item[param_name] = initial_value

            return additional_item

        else:
            raise ResourceProcessingError(
                f"Two resources with equal names were found! "
                f"Name: '{additional_item_name}', first resource type: "
                f"'{initial_type}', second resource type: "
                f"'{additional_type}'. \nPlease, rename one of them!"
            )


def _merge_api_gw_list_typed_configurations(initial_resource: dict,
                                            additional_resource: dict,
                                            property_names_list: list,
                                            additional_item_name: str):
    for property_name in property_names_list:
        initial_property_value = initial_resource.get(property_name, [])
        additional_resource_value = additional_resource.get(property_name, [])
        for each in initial_property_value:
            if each in additional_resource_value:
                raise ResourceMetadataError(
                    f"Unable to merge the API Gateway "
                    f"'{additional_item_name}' definition because "
                    f"of duplication of the parameter '{property_name}' "
                    f"in different deployment resources files. "
                    f"Please resolve the conflict."
                )

        additional_resource[
            property_name] = initial_property_value + additional_resource_value
    return additional_resource


def _populate_s3_path_python_node_dotnet(meta, bundle_name):
    name = meta.get('name')
    version = meta.get('version')
    prefix = meta.pop('prefix', None)
    suffix = meta.pop('suffix', None)
    if not name or not version:
        raise ParameterError(
            "Lambda config must contain name and version. Existing "
            f"configuration: '{prettify_json(meta)}'"
        )
    else:
        if prefix:
            name = name[len(prefix):]
        if suffix:
            name = name[:-len(suffix)]
        meta[S3_PATH_NAME] = build_path(bundle_name,
                                        build_py_package_name(name, version))


def _populate_s3_path_java(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise ParameterError(
            "Lambda config must contain deployment_package. Existing "
            f"configuration: '{prettify_json(meta)}'"
        )
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def _populate_s3_path_lambda(meta, bundle_name):
    runtime = meta.get('runtime')
    if not runtime:
        raise ParameterError(
            "Lambda config must contain runtime. "
            f"Existing configuration: '{prettify_json(meta)}'"
        )
    resolver_func = RUNTIME_PATH_RESOLVER.get(runtime.lower())
    if resolver_func:
        resolver_func(meta, bundle_name)
    else:
        raise InvalidValueError(
            f"Specified runtime '{runtime.lower()}' in '{meta.get('name')}' "
            f"is not supported. Supported runtimes: "
            f"'{list(RUNTIME_PATH_RESOLVER.keys())}'"
        )


def _populate_s3_path_lambda_layer(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise ParameterError(
            "Lambda Layer config must contain deployment_package. "
            f"'Existing configuration: '{prettify_json(meta)}'"
        )
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def _populate_s3_path_ebs(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise ParameterError(
            "Beanstalk_app config must contain deployment_package. "
            f"Existing configuration: '{prettify_json(meta)}'"
        )
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def _populate_s3_path_swagger_ui(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise ParameterError(
            "Swagger UI config must contain deployment_package. "
            f"Existing configuration: '{prettify_json(meta)}'"
        )
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def populate_s3_paths(overall_meta, bundle_name):
    for name, meta in overall_meta.items():
        resource_type = meta.get('resource_type')
        mapping_func = S3_PATH_MAPPING.get(resource_type)
        if mapping_func:
            mapping_func(meta, bundle_name)
    return overall_meta


def extract_deploy_stage_from_openapi_spec(openapi_spec: dict) -> str:
    """
    Extract the first path segment from the server URL in an API specification.
    If no server URL is found, or there is no path segment, raise an exception.
    """

    servers = openapi_spec.get('servers', [])
    if not servers:
        raise ParameterError(
            "No server information found in API specification."
        )

    server_url = servers[0].get('url', '')
    variables = servers[0].get('variables', {})

    # Substitute variables in the URL template with their default values,if any
    for var_name, var_details in variables.items():
        default_value = var_details.get('default', '')
        server_url = server_url.replace(f'{{{var_name}}}', default_value)

    # Extract the first path segment
    path_segments = [segment for segment in
                     urlparse(server_url).path.split('/')
                     if segment]
    if not path_segments:
        raise InvalidValueError("No path segments found in server URL.")

    return path_segments[0]


RUNTIME_PATH_RESOLVER = {
    'python3.9': _populate_s3_path_python_node_dotnet,
    'python3.10': _populate_s3_path_python_node_dotnet,
    'python3.11': _populate_s3_path_python_node_dotnet,
    'python3.12': _populate_s3_path_python_node_dotnet,
    'python3.13': _populate_s3_path_python_node_dotnet,
    'java11': _populate_s3_path_java,
    'java17': _populate_s3_path_java,
    'java21': _populate_s3_path_java,
    'nodejs18.x': _populate_s3_path_python_node_dotnet,
    'nodejs20.x': _populate_s3_path_python_node_dotnet,
    'nodejs22.x': _populate_s3_path_python_node_dotnet,
    'dotnet8': _populate_s3_path_python_node_dotnet
}

S3_PATH_MAPPING = {
    LAMBDA_TYPE: _populate_s3_path_lambda,
    EBS_TYPE: _populate_s3_path_ebs,
    LAMBDA_LAYER_TYPE: _populate_s3_path_lambda_layer,
    SWAGGER_UI_TYPE: _populate_s3_path_swagger_ui
}


def _look_for_configs(nested_files: list[str], resources_meta: dict[str, Any],
                      path: str, bundle_name: str) -> None:
    """ Look for all config files in project structure. Read content and add
    all meta to overall meta if there is no duplicates. If duplicates found -
    raise an exception.

    :param nested_files: A list of files in the project
    :param resources_meta: A dictionary of resources metadata
    :param path: A string path to the project
    :param bundle_name: A string name of the bundle
    """
    for each in nested_files:
        if each.endswith(LAMBDA_CONFIG_FILE_NAME) or \
                each.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME) or \
                each.endswith(SWAGGER_UI_CONFIG_FILE_NAME) or \
                each.endswith(APPSYNC_CONFIG_FILE_NAME):
            resource_config_path = os.path.join(path, each)
            _LOG.debug(f'Processing file: {resource_config_path}')
            with open(resource_config_path) as data_file:
                resource_conf = load(data_file)

            resource_name = resource_conf['name']
            resource_type = resource_conf['resource_type']
            _LOG.debug(f'Found {resource_type}: {resource_name}')
            res = _check_duplicated_resources(resources_meta, resource_name,
                                              resource_conf)
            if res:
                resource_conf = res
            resources_meta[resource_name] = resource_conf

        if each.endswith(OAS_V3_FILE_NAME):
            openapi_spec_path = os.path.join(path, each)
            _LOG.debug(f'Processing file: {openapi_spec_path}')
            with open(openapi_spec_path) as data_file:
                openapi_spec = load(data_file)

            api_gateway_name = openapi_spec['info']['title']
            _LOG.debug(f'Found API Gateway: {api_gateway_name}')
            deploy_stage = extract_deploy_stage_from_openapi_spec(openapi_spec)
            resource = {
                "definition": openapi_spec,
                "resource_type": API_GATEWAY_OAS_V3_TYPE,
                "deploy_stage": deploy_stage,
            }
            tags = openapi_spec.get("x-syndicate-openapi-tags")
            if tags:
                resource["tags"] = tags
            res = _check_duplicated_resources(
                resources_meta, api_gateway_name, resource
            )
            if res:
                resource = res
            resources_meta[api_gateway_name] = resource

        if each == RESOURCES_FILE_NAME:
            additional_config_path = os.path.join(path, RESOURCES_FILE_NAME)
            _LOG.debug('Processing file: {0}'.format(additional_config_path))
            with open(additional_config_path, encoding='utf-8') as json_file:
                deployment_resources = load(json_file)
            for resource_name in deployment_resources:
                _LOG.debug('Found resource ' + resource_name)
                resource = deployment_resources[resource_name]
                # check if resource type exists in deployment framework and
                #  has resource_type field
                try:
                    resource_type = resource['resource_type']
                except KeyError:
                    error_message = (
                        f"There is no 'resource_type' in {resource_name} "
                        f"metadata"
                    )
                    _LOG.error(error_message)
                    raise ParameterError(error_message)
                if resource_type not in RESOURCE_LIST:
                    error_message = (
                        f'Unsupported resource type found: "{resource_type}". '
                        f'Please double-check the correctness of the specified '
                        f'resource type. To add a new resource type please '
                        f'request the support team.')
                    _LOG.error(error_message)
                    raise InvalidValueError(error_message)
                res = _check_duplicated_resources(resources_meta,
                                                  resource_name, resource)
                if res:
                    resource = res
                resources_meta[resource_name] = resource


# todo validate all required configs
def create_resource_json(project_path: str, bundle_name: str) -> dict[
    str, Any]:
    """ Create resource catalog json with all resource metadata in project.

    :param project_path: path to the project
    :type bundle_name: name of the bucket subdir
    """
    resources_meta = {}

    # Walking through every folder in the project
    for path, _, nested_items in os.walk(project_path):
        # there is no duplicates in single json, because json is a dict

        _look_for_configs(nested_items, resources_meta, path, bundle_name)

    meta_for_validation = _resolve_aliases(resources_meta)
    # check if all dependencies were described
    common_validator = VALIDATOR_BY_TYPE_MAPPING[ALL_TYPES]
    for name, meta in meta_for_validation.items():
        common_validator(resource_name=name,
                         resource_meta=meta, all_meta=meta_for_validation)

        resource_type = meta['resource_type']
        type_validator = VALIDATOR_BY_TYPE_MAPPING.get(resource_type)
        if type_validator:
            type_validator(name, meta)

    return resources_meta


def _resolve_names_in_meta(resources_dict, old_value, new_value):
    resource_name_placeholder = '$rn{' + old_value + '}'
    if isinstance(resources_dict, dict):
        for k, v in resources_dict.items():
            if k in NAME_RESOLVING_BLACKLISTED_KEYS:
                continue
            if isinstance(v, str) and old_value == v:
                resources_dict[k] = v.replace(old_value, new_value)
            elif isinstance(v, str) and old_value in v and v.startswith('arn'):
                resources_dict[k] = _resolve_name_in_arn(v, old_value, new_value)
            elif isinstance(v, str) and resource_name_placeholder in v:
                resources_dict[k] = v.replace(resource_name_placeholder, new_value)
            else:
                _resolve_names_in_meta(v, old_value, new_value)
    elif isinstance(resources_dict, list):
        for item in resources_dict:
            if isinstance(item, dict):
                _resolve_names_in_meta(item, old_value, new_value)
            elif (isinstance(item, str) and old_value in item and
                  item.startswith('arn')):
                index = resources_dict.index(item)
                resources_dict[index] = _resolve_name_in_arn(item, old_value, new_value)
            elif isinstance(item, str) and resource_name_placeholder in item:
                index = resources_dict.index(item)
                resources_dict[index] = item.replace(resource_name_placeholder, new_value)
            elif isinstance(item, str):
                if item == old_value:
                    index = resources_dict.index(old_value)
                    del resources_dict[index]
                    resources_dict.append(new_value)


def _resolve_name_in_arn(arn, old_value, new_value):
    from syndicate.core import CONFIG

    extended_prefix_mode = CONFIG.extended_prefix_mode
    arn_parts = arn.split(':')
    for part in arn_parts:
        new_part = None
        if part == old_value:
            new_part = new_value
        elif part.startswith(old_value) and part[len(old_value)] == '/':
            new_part = part.replace(old_value, new_value)
        elif part.endswith(old_value) and part[:-len(old_value)].endswith('/'):
            # to resolve resources with prefixes like ":role/", ":topic/", etc.
            resource_prefix = part[:-len(old_value)]
            if resource_prefix in GLOBAL_AWS_SERVICE_PREFIXES \
                    or extended_prefix_mode:
                new_part = part.replace(old_value, new_value)
        if new_part:
            index = arn_parts.index(part)
            arn_parts[index] = new_part
    return ':'.join(arn_parts)


def create_meta(project_path: str, bundle_name: str) -> None:
    from syndicate.core.build.runtime.java import safe_resolve_mvn_path
    from syndicate.core import PROJECT_STATE

    # create overall meta.json with all resource meta info
    meta_path = build_path(project_path, ARTIFACTS_FOLDER,
                           bundle_name)
    _LOG.info(f'Bundle path: {meta_path}')
    overall_meta = create_resource_json(project_path=project_path,
                                        bundle_name=bundle_name)
    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)
    write_content_to_file(bundle_dir, BUILD_META_FILE_NAME, overall_meta)

    PROJECT_STATE.refresh_state()
    build_mapping_dict = PROJECT_STATE.load_project_build_mapping()
    is_java_exists = RUNTIME_JAVA in (build_mapping_dict or {})

    if is_java_exists:
        mvn_path = safe_resolve_mvn_path()
        mvn_clean_command = [mvn_path, 'clean']

        java_root_path_japp = build_path(project_path, JAVA_ROOT_DIR_JAPP)
        java_root_path_japp_pom = build_path(java_root_path_japp, FILE_POM)
        project_path_pom = build_path(project_path, FILE_POM)

        if os.path.exists(java_root_path_japp_pom):
            execute_command_by_path(
                command=mvn_clean_command,
                path=java_root_path_japp,
                shell=False
            )
            _LOG.info(
                f"Cleaned up the Java project in {JAVA_ROOT_DIR_JAPP!r} "
                f"after building"
            )
        elif os.path.exists(project_path_pom):
            execute_command_by_path(
                command=mvn_clean_command,
                path=project_path,
                shell=False
            )
            _LOG.info(
                "Cleaned up the Java project in the base project directory "
                "after building"
            )


def resolve_meta(overall_meta):
    from syndicate.core import CONFIG
    iam_suffix = CONFIG.iam_suffix
    extended_prefix_mode = CONFIG.extended_prefix_mode
    overall_meta = _resolve_aliases(overall_meta)
    detect_unresolved_aliases(overall_meta)
    _LOG.debug('Resolved meta was created')
    _LOG.debug(prettify_json(overall_meta))
    _resolve_permissions_boundary(overall_meta)
    _LOG.debug('Permissions boundary were resolved')
    # get dict with resolved prefix and suffix in meta resources
    # key: current_name, value: resolved_name
    resolved_names = {}
    for name, res_meta in overall_meta.items():
        if res_meta.get('external'):
            continue
        resource_type = res_meta['resource_type']
        if resource_type in GLOBAL_AWS_SERVICES or extended_prefix_mode:
            resolved_name = resolve_resource_name(
                resource_name=name,
                prefix=CONFIG.resources_prefix,
                suffix=CONFIG.resources_suffix)
            if resource_type == LAMBDA_TYPE:
                res_meta['prefix'] = CONFIG.resources_prefix
                res_meta['suffix'] = CONFIG.resources_suffix
            # add iam_suffix to IAM role only if it is specified in config file
            if resource_type == IAM_ROLE and iam_suffix:
                resolved_name = resolved_name + iam_suffix
            if name != resolved_name:
                resolved_names[name] = resolved_name
    _LOG.debug('Going to resolve names in meta')
    _LOG.debug(f'Resolved names mapping: {str(resolved_names)}')
    for current_name, resolved_name in resolved_names.items():
        overall_meta[resolved_name] = overall_meta.pop(current_name)
        if not all([current_name, resolved_name]):
            continue
        _resolve_names_in_meta(overall_meta, current_name, resolved_name)
    return overall_meta


def resolve_tags(meta: dict) -> None:
    _LOG.debug('Going to resolve resources tags.')
    from syndicate.core import CONFIG
    common_tags = CONFIG.tags
    for res_name, res_meta in meta.items():
        res_tags = res_meta.get('tags', {})
        _LOG.debug(f'The resource {res_name} tags: {res_tags}')
        errors = validate_tags('tags', res_tags)
        if errors:
            USER_LOG.warn(
                f'The resource {res_name} tags don\'t pass validation and '
                f'will be removed from the resource meta. Details "{errors}"')
            res_meta.pop('tags')
            continue
        overall_tags = _format_tags(res_meta['resource_type'],
                                    {**common_tags, **res_tags})
        _LOG.debug(f'Resolved resource {res_name} tags {overall_tags}')
        res_meta['tags'] = overall_tags


def preprocess_tags(output: dict):
    for item in output.values():
        res_meta = item['resource_meta']
        tags = res_meta.get('tags')

        match tags:
            case tags if isinstance(tags, dict):
                continue
            case tags if isinstance(tags, list):
                res_meta['tags'] = _tags_to_dict(tags)
            case _:
                res_meta.pop('tags', None)


def _tags_to_dict(tags: list) -> dict:
    result = {}
    for tag in tags:
        tag_key = None
        tag_value = ''
        for k, v in tag.items():
            if k.lower() == 'key':
                tag_key = v
            if k.lower() == 'value':
                tag_value = v
        if tag_key is not None:
            result.update({tag_key: tag_value})
    return result


def _format_tags(res_type: str, tags: dict) -> dict | list:
    match res_type:
        case res_type if (res_type in
                          TAGS_RESOURCE_TYPE_CONFIG['capitalised_keys_list']):
            return [{'Key': k, 'Value': v} for k, v in tags.items()]
        case res_type if (res_type in
                          TAGS_RESOURCE_TYPE_CONFIG['lover_case_keys_list']):
            return [{'key': k, 'value': v} for k, v in tags.items()]
        case res_type if res_type in TAGS_RESOURCE_TYPE_CONFIG['untaggable']:
            _LOG.debug(f'The resource type {res_type} can not be tagged')
            return {}
        case _:
            return tags


def _resolve_aliases(overall_meta):
    """
    :type overall_meta: dict
    """
    from syndicate.core import CONFIG
    if CONFIG.aliases:
        aliases = {'${' + key + '}': str(value) for key, value in
                   CONFIG.aliases.items()}
        overall_meta = resolve_dynamic_identifier(aliases, overall_meta)
    return overall_meta


def _resolve_permissions_boundary(overall_meta):
    """Adds to every resource with resource_type IAM_ROLE permissions boundary
    from the config"""
    from syndicate.core import CONFIG
    if CONFIG.iam_permissions_boundary:
        for name, meta in overall_meta.items():
            if meta.get('resource_type') == IAM_ROLE:
                meta['permissions_boundary'] = CONFIG.iam_permissions_boundary


def resolve_resource_name(resource_name, prefix=None, suffix=None):
    return _resolve_suffix_name(
        _resolve_prefix_name(resource_name, prefix), suffix)


def resolve_resource_name_by_data(resource_name, resource_prefix,
                                  resource_suffix):
    return _resolve_suffix_name(
        _resolve_prefix_name(resource_name, resource_prefix), resource_suffix)


def _resolve_prefix_name(resource_name, resource_prefix):
    if resource_prefix:
        return resolve_aliases_for_string(resource_prefix) + resource_name
    return resource_name


def _resolve_suffix_name(resource_name, resource_suffix):
    if resource_suffix:
        return resource_name + resolve_aliases_for_string(resource_suffix)
    return resource_name


def get_meta_from_output(output: dict):
    from syndicate.core import CONFIG
    meta = {}
    for arn, data in output.items():
        resource_meta = data.get('resource_meta')
        resource_name = data.get('resource_name')

        suffix_index = resource_name.rfind(CONFIG.resources_suffix)
        if suffix_index != -1:  # if found
            resource_name = \
                resource_name[:suffix_index] + \
                resource_name[suffix_index + len(CONFIG.resources_suffix):]

        prefix_index = resource_name.find(CONFIG.resources_prefix)
        if prefix_index != -1:
            resource_name = \
                resource_name[:prefix_index] + \
                resource_name[prefix_index + len(CONFIG.resources_prefix):]

        meta.update({resource_name: resource_meta})

    return meta
