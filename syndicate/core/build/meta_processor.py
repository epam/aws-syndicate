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
from json import load

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import (build_py_package_name,
                                         resolve_bundle_directory)
from syndicate.core.build.validator.mapping import (VALIDATOR_BY_TYPE_MAPPING,
                                                    ALL_TYPES)
from syndicate.core.conf.processor import GLOBAL_AWS_SERVICES
from syndicate.core.constants import (API_GATEWAY_TYPE, ARTIFACTS_FOLDER,
                                      BUILD_META_FILE_NAME, EBS_TYPE,
                                      LAMBDA_CONFIG_FILE_NAME, LAMBDA_TYPE,
                                      RESOURCES_FILE_NAME, RESOURCE_LIST,
                                      IAM_ROLE, LAMBDA_LAYER_TYPE,
                                      S3_PATH_NAME, LAMBDA_LAYER_CONFIG_FILE_NAME,
                                      WEB_SOCKET_API_GATEWAY_TYPE)
from syndicate.core.helper import (build_path, prettify_json,
                                   resolve_aliases_for_string,
                                   write_content_to_file)
from syndicate.core.resources.helper import resolve_dynamic_identifier

DEFAULT_IAM_SUFFIX_LENGTH = 5

_LOG = get_logger('syndicate.core.build.meta_processor')


def validate_deployment_packages(bundle_path, meta_resources):
    package_paths = artifact_paths(meta_resources)
    nonexistent_packages = []
    for package in package_paths:
        package_path = build_path(bundle_path, package)
        if not os.path.exists(package_path):
            nonexistent_packages.append(package_path)

    if nonexistent_packages:
        raise AssertionError('Bundle is not properly configured.'
                             ' Nonexistent deployment packages: '
                             '{0}'.format(prettify_json(nonexistent_packages)))


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
        initial_item = initial_meta_dict.get(additional_item_name)
        if not initial_item:
            return
        initial_type = initial_item['resource_type']
        if additional_type == initial_type and initial_type in \
                {API_GATEWAY_TYPE, WEB_SOCKET_API_GATEWAY_TYPE}:
            # check if APIs have same resources
            for each in list(initial_item['resources'].keys()):
                if each in list(additional_item['resources'].keys()):
                    raise AssertionError(
                        "API '{0}' has duplicated resource '{1}'! Please, "
                        "change name of one resource or remove one.".format(
                            additional_item_name, each))
                    # check is APIs have once described cache configuration
            initial_cache_config = initial_item.get(
                'cluster_cache_configuration')
            additional_cache_config = additional_item.get(
                'cluster_cache_configuration')
            if initial_cache_config and additional_cache_config:
                raise AssertionError(
                    "API '{0}' has duplicated cluster cache configurations. "
                    "Please, remove one cluster cache configuration.".format(
                        additional_item_name)
                )
            if initial_cache_config:
                additional_item[
                    'cluster_cache_configuration'] = initial_cache_config
            # handle responses
            initial_responses = initial_item.get(
                'api_method_responses')
            additional_responses = additional_item.get(
                'api_method_responses')
            if initial_responses and additional_responses:
                raise AssertionError(
                    "API '{0}' has duplicated api method responses "
                    "configurations. Please, remove one "
                    "api method responses configuration.".format(
                        additional_item_name)
                )
            if initial_responses:
                additional_item[
                    'api_method_responses'] = initial_responses
            # handle integration responses
            initial_integration_resp = initial_item.get(
                'api_method_integration_responses')
            additional_integration_resp = additional_item.get(
                'api_method_integration_responses')
            if initial_integration_resp and additional_integration_resp:
                raise AssertionError(
                    "API '{0}' has duplicated api method integration "
                    "responses configurations. Please, remove one "
                    "api method integration responses configuration.".format(
                        additional_item_name)
                )
            if initial_integration_resp:
                additional_item[
                    'api_method_integration_responses'] = initial_integration_resp
            # join items dependencies
            dependencies_dict = {each['resource_name']: each
                                 for each in additional_item.get('dependencies') or []}
            for each in initial_item.get('dependencies') or []:
                if each['resource_name'] not in dependencies_dict:
                    additional_item['dependencies'].append(each)
            # join items resources
            additional_item['resources'].update(initial_item['resources'])
            # return aggregated API description
            init_deploy_stage = initial_item.get('deploy_stage')
            if init_deploy_stage:
                additional_item['deploy_stage'] = init_deploy_stage

            init_compression = initial_item.get("minimum_compression_size")
            if init_compression:
                additional_comp_size = \
                    additional_item.get('minimum_compression_size')
                if additional_comp_size:
                    _LOG.warn(f"Found 'minimum_compression_size': "
                              f"{init_compression} inside root "
                              f"deployment_resources. The value "
                              f"'{additional_comp_size}' from: "
                              f"{additional_item} will be overwritten")
                additional_item['minimum_compression_size'] = init_compression

            # join authorizers
            initial_authorizers = initial_item.get('authorizers') or {}
            additional_authorizers = additional_item.get('authorizers') or {}
            additional_item['authorizers'] = {**initial_authorizers,
                                              **additional_authorizers}
            # join models
            initial_models = initial_item.get('models') or {}
            additional_models = additional_item.get('models') or {}
            additional_item['models'] = {**initial_models, **additional_models}
            # policy statement singleton
            _pst = initial_item.get('policy_statement_singleton')
            if 'policy_statement_singleton' not in additional_item and _pst:
                additional_item['policy_statement_singleton'] = _pst

            additional_item['route_selection_expression'] = initial_item.get('route_selection_expression')

            additional_item = _merge_api_gw_list_typed_configurations(
                initial_item,
                additional_item,
                ['binary_media_types', 'apply_changes']
            )

            return additional_item

        elif additional_type == initial_type:
            if additional_item == initial_item:
                raise AssertionError(
                    'Warn. Two equals resources descriptions were found! '
                    'Please, remove one of them. Resource name:'
                    ' {0}'.format(additional_item_name))
            else:
                raise AssertionError(
                    "Error! Two resources with equal names were found! Name:"
                    " {0}. Please, rename one of them. First resource: {1}. "
                    "Second resource: {2}".format(additional_item_name,
                                                  initial_item,
                                                  additional_item))


def _merge_api_gw_list_typed_configurations(initial_resource,
                                            additional_resource,
                                            property_names_list):
    for property_name in property_names_list:
        initial_property_value = initial_resource.get(property_name, [])
        additional_resource_value = additional_resource.get(property_name, [])
        additional_resource[
            property_name] = initial_property_value + additional_resource_value
    return additional_resource


def _populate_s3_path_python_node(meta, bundle_name):
    name = meta.get('name')
    version = meta.get('version')
    prefix = meta.get('prefix')
    suffix = meta.get('suffix')
    if not name or not version:
        raise AssertionError('Lambda config must contain name and version. '
                             'Existing configuration'
                             ': {0}'.format(prettify_json(meta)))
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
        raise AssertionError('Lambda config must contain deployment_package. '
                             'Existing configuration'
                             ': {0}'.format(prettify_json(meta)))
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def _populate_s3_path_lambda(meta, bundle_name):
    runtime = meta.get('runtime')
    if not runtime:
        raise AssertionError(
            'Lambda config must contain runtime. '
            'Existing configuration: {0}'.format(prettify_json(meta)))
    resolver_func = RUNTIME_PATH_RESOLVER.get(runtime.lower())
    if resolver_func:
        resolver_func(meta, bundle_name)
    else:
        raise AssertionError(
            'Specified runtime {0} in {1} is not supported. '
            'Supported runtimes: {2}'.format(
                runtime.lower(), meta.get('name'),
                list(RUNTIME_PATH_RESOLVER.keys())))


def _populate_s3_path_lambda_layer(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise AssertionError(
            'Lambda Layer config must contain deployment_package. '
            'Existing configuration'
            ': {0}'.format(prettify_json(meta)))
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def _populate_s3_path_ebs(meta, bundle_name):
    deployment_package = meta.get('deployment_package')
    if not deployment_package:
        raise AssertionError('Beanstalk_app config must contain '
                             'deployment_package. Existing configuration'
                             ': {0}'.format(prettify_json(meta)))
    else:
        meta[S3_PATH_NAME] = build_path(bundle_name, deployment_package)


def populate_s3_paths(overall_meta, bundle_name):
    for name, meta in overall_meta.items():
        resource_type = meta.get('resource_type')
        mapping_func = S3_PATH_MAPPING.get(resource_type)
        if mapping_func:
            mapping_func(meta, bundle_name)
    return overall_meta


RUNTIME_PATH_RESOLVER = {
    'python3.6': _populate_s3_path_python_node,
    'python3.7': _populate_s3_path_python_node,
    'python3.8': _populate_s3_path_python_node,
    'python3.9': _populate_s3_path_python_node,
    'python3.10': _populate_s3_path_python_node,
    'python3.11': _populate_s3_path_python_node,
    'java8': _populate_s3_path_java,
    'java8.al2': _populate_s3_path_java,
    'java11': _populate_s3_path_java,
    'nodejs10.x': _populate_s3_path_python_node,
    'nodejs14.x': _populate_s3_path_python_node,
    'nodejs12.x': _populate_s3_path_python_node
}

S3_PATH_MAPPING = {
    LAMBDA_TYPE: _populate_s3_path_lambda,
    EBS_TYPE: _populate_s3_path_ebs,
    LAMBDA_LAYER_TYPE: _populate_s3_path_lambda_layer
}


def _look_for_configs(nested_files, resources_meta, path, bundle_name):
    """ Look for all config files in project structure. Read content and add
    all meta to overall meta if there is no duplicates. If duplicates found -
    raise AssertionError.

    :type nested_files: list
    :type resources_meta: dict
    :type path: str
    """
    for each in nested_files:
        if each.endswith(LAMBDA_CONFIG_FILE_NAME) or each.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
            lambda_config_path = os.path.join(path, each)
            _LOG.debug('Processing file: {0}'.format(lambda_config_path))
            with open(lambda_config_path) as data_file:
                lambda_conf = load(data_file)

            lambda_name = lambda_conf['name']
            _LOG.debug('Found lambda: {0}'.format(lambda_name))
            res = _check_duplicated_resources(resources_meta, lambda_name,
                                              lambda_conf)
            if res:
                lambda_conf = res
            resources_meta[lambda_name] = lambda_conf

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
                    raise AssertionError(
                        "There is not 'resource_type' in {0}".format(
                            resource_name))
                if resource_type not in RESOURCE_LIST:
                    raise KeyError(
                        "You specified new resource type in configuration"
                        " file {0}, but it doesn't have creation function."
                        " Please, add new creation function or change "
                        "resource name with existing one.".format(
                            resource_type))
                res = _check_duplicated_resources(resources_meta,
                                                  resource_name, resource)
                if res:
                    resource = res
                resources_meta[resource_name] = resource


# todo validate all required configs
def create_resource_json(project_path, bundle_name):
    """ Create resource catalog json with all resource metadata in project.
    :param project_path: path to the project
    :type bundle_name: name of the bucket subdir
    """
    resources_meta = {}

    for path, _, nested_items in os.walk(project_path):
        # there is no duplicates in single json, because json is a dict

        _look_for_configs(nested_items, resources_meta, path, bundle_name)

    meta_for_validation = _resolve_aliases(resources_meta)
    # check if all dependencies were described
    common_validator = VALIDATOR_BY_TYPE_MAPPING[ALL_TYPES]
    for name, meta in meta_for_validation.items():
        common_validator(resource_meta=meta, all_meta=meta_for_validation)

        resource_type = meta['resource_type']
        type_validator = VALIDATOR_BY_TYPE_MAPPING.get(resource_type)
        if type_validator:
            type_validator(name, meta)

    return resources_meta


def _resolve_names_in_meta(resources_dict, old_value, new_value):
    if isinstance(resources_dict, dict):
        for k, v in resources_dict.items():
            # if k == old_value:
            #     resources_dict[new_value] = resources_dict.pop(k)
            if isinstance(v, str) and old_value == v:
                resources_dict[k] = v.replace(old_value, new_value)
            elif isinstance(v, str) and old_value in v and v.startswith('arn'):
                resources_dict[k] = v.replace(old_value, new_value)
            else:
                _resolve_names_in_meta(v, old_value, new_value)
    elif isinstance(resources_dict, list):
        for item in resources_dict:
            if isinstance(item, dict):
                _resolve_names_in_meta(item, old_value, new_value)
            elif isinstance(item, str):
                if item == old_value:
                    index = resources_dict.index(old_value)
                    del resources_dict[index]
                    resources_dict.append(new_value)


def create_meta(project_path, bundle_name):
    # create overall meta.json with all resource meta info
    meta_path = build_path(project_path, ARTIFACTS_FOLDER,
                           bundle_name)
    _LOG.info("Bundle path: {0}".format(meta_path))
    overall_meta = create_resource_json(project_path=project_path,
                                        bundle_name=bundle_name)
    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)
    write_content_to_file(bundle_dir, BUILD_META_FILE_NAME, overall_meta)


def resolve_meta(overall_meta):
    from syndicate.core import CONFIG
    iam_suffix = _resolve_iam_suffix(iam_suffix=CONFIG.iam_suffix)
    extended_prefix_mode = CONFIG.extended_prefix_mode
    overall_meta = _resolve_aliases(overall_meta)
    _LOG.debug('Resolved meta was created')
    _LOG.debug(prettify_json(overall_meta))
    _resolve_permissions_boundary(overall_meta)
    _LOG.debug('Permissions boundary were resolved')
    # get dict with resolved prefix and suffix in meta resources
    # key: current_name, value: resolved_name
    resolved_names = {}
    for name, res_meta in overall_meta.items():
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
    _LOG.debug('Resolved names mapping: {0}'.format(str(resolved_names)))
    for current_name, resolved_name in resolved_names.items():
        overall_meta[resolved_name] = overall_meta.pop(current_name)
        _resolve_names_in_meta(overall_meta, current_name, resolved_name)
    return overall_meta


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


def _resolve_iam_suffix(suffix_len=DEFAULT_IAM_SUFFIX_LENGTH, iam_suffix=None):
    """
    This method adds additional suffix to iam roles.
    The suffix could be passed to the method. Otherwise it will be generated
    as a random string with the combination of lowercase letters.
    """
    if not iam_suffix:
        return None
    if suffix_len > DEFAULT_IAM_SUFFIX_LENGTH:
        raise AssertionError(
            'Additional suffix for IAM roles should be maximum'
            '{0} symbols in length. Provided: {1}'.format(
                DEFAULT_IAM_SUFFIX_LENGTH, suffix_len))

    # check and use provided
    provided_max_len = DEFAULT_IAM_SUFFIX_LENGTH
    if len(iam_suffix) > provided_max_len:
        raise AssertionError(
            'Provided additional suffix for IAM roles should be maximum'
            '{0} symbols in length. Provided len: {1}; Suffix: {2}'.format(
                provided_max_len, len(iam_suffix), iam_suffix))
    return iam_suffix
