import json
from typing import Optional

from smoke.commons.checkers import TYPE_MODIFICATION_FUNC_MAPPING, \
    exit_code_checker, artifacts_existence_checker, deployment_output_checker, \
    build_meta_checker, TYPE_EXISTENCE_FUNC_MAPPING
from smoke.commons.utils import populate_prefix_suffix
from tests.smoke.commons import connections
from tests.smoke.commons.connections import get_s3_bucket_file_content
from tests.smoke.commons.constants import DEPLOY_OUTPUT_DIR, \
    RESOURCE_TYPE_CONFIG_PARAM, BUNDLE_NAME, DEPLOY_NAME, \
    SWAGGER_UI_RESOURCE_TYPE


def exit_code_handler(actual_exit_code: int, expected_exit_code: int,
                      **kwargs):

    return True if exit_code_checker(actual_exit_code, expected_exit_code) \
        else {'expected_exit_code': expected_exit_code,
              'actual_exit_code': actual_exit_code}


def artifacts_existence_handler(artifacts_list: list,
                                deploy_target_bucket: str,
                                succeeded_deploy: Optional[bool] = None,
                                **kwargs):
    missing_resources = []
    for artifact in artifacts_list:
        if succeeded_deploy is not None:
            file_key = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{artifact}'
        else:
            file_key = f'{BUNDLE_NAME}/{artifact}'
        if not artifacts_existence_checker(file_key, deploy_target_bucket):
            missing_resources.append(artifact)
    return {'missing_resources': missing_resources} \
        if missing_resources else True


def build_meta_handler(resources: dict, deploy_target_bucket: str, **kwargs):
    build_meta = connections.get_s3_bucket_file_content(
        bucket_name=deploy_target_bucket,
        file_key=f'{BUNDLE_NAME}/build_meta.json')
    if not build_meta:
        return False

    build_meta_json = json.loads(build_meta)

    return build_meta_checker(build_meta_json, resources)


def deployment_output_handler(deploy_target_bucket: str, resources: dict,
                              succeeded_deploy: bool = True,
                              prefix: Optional[str] = None,
                              suffix: Optional[str] = None, **kwargs):
    if succeeded_deploy:
        output_path = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}.json'
    else:
        output_path = \
            f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}_failed.json'

    output = get_s3_bucket_file_content(deploy_target_bucket, output_path)
    output_json = json.loads(output)
    return deployment_output_checker(
        output_json,
        populate_prefix_suffix(resources, prefix, suffix))


def resource_existence_handler(resources: dict, deploy_target_bucket: str,
                               suffix: Optional[str] = None,
                               prefix: Optional[str] = None, **kwargs):
    results = {}
    resources = populate_prefix_suffix(resources, prefix, suffix)

    non_existent_resources = {}
    non_checked_resources = {}
    for res_name, res_meta in resources.items():
        res_type = res_meta[RESOURCE_TYPE_CONFIG_PARAM]
        func = TYPE_EXISTENCE_FUNC_MAPPING.get(res_type)
        if not func:
            print(f'Unknown resource type `{res_type}`')
            non_checked_resources[res_name] = res_type
            continue
        if res_type == SWAGGER_UI_RESOURCE_TYPE:
            is_exist = func(res_name, deploy_target_bucket)
        else:
            is_exist = func(res_name)
        if not is_exist:
            non_existent_resources[res_name] = res_meta

    if non_existent_resources:
        results['non_existent_resources'] = non_existent_resources
    if non_checked_resources:
        results['non_checked_resources'] = non_checked_resources

    return results if results else True


def resource_modification_handler(resources: dict, update_time: str,
                                  suffix: Optional[str] = None,
                                  prefix: Optional[str] = None, **kwargs):
    result = []
    for resource_name, resource_type in resources.items():
        resource_typename = resource_type[RESOURCE_TYPE_CONFIG_PARAM]
        func = TYPE_MODIFICATION_FUNC_MAPPING.get(resource_typename)
        if not func:
            print(f'Unknown resource type `{resource_typename}`')
            continue
        is_modified = func(update_time=update_time,
                           resource_name=f'{prefix}{resource_name}{suffix}')
        if is_modified is not True:
            result.append(resource_name)
    return {'unmodified_resources': result} if result else True


HANDLERS_MAPPING = {
    'exit_code': exit_code_handler,
    'artifacts_existence': artifacts_existence_handler,
    'build_meta': build_meta_handler,
    'deployment_output': deployment_output_handler,
    'resource_existence': resource_existence_handler,
    'resource_modification': resource_modification_handler
}
