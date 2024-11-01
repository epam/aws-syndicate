import copy
from datetime import datetime
from typing import Optional

from tests.smoke.commons import connections
from tests.smoke.commons.connections import get_s3_bucket_file_content
from tests.smoke.commons.constants import DEPLOY_OUTPUT_DIR, \
    RESOURCE_TYPE_CONFIG_PARAM, BUNDLE_NAME


def exit_code(actual_exit_code: int, expected_exit_code: int, **kwargs):
    return actual_exit_code == expected_exit_code


def artifacts_existence(artifacts_list: list, deploy_target_bucket: str,
                        suffix: Optional[str] = None,
                        prefix: Optional[str] = None, **kwargs):
    missing_resources = []
    for artifact in artifacts_list:
        exist = connections.get_s3_bucket_object(
            bucket_name=deploy_target_bucket,
            file_key=BUNDLE_NAME + '/' + artifact)
        if not exist:
            missing_resources.append(artifact)
    return {'missing_resources': missing_resources} \
        if missing_resources else True


def build_meta(resources: dict, suffix: Optional[str] = None,
               prefix: Optional[str] = None, **kwargs):
    ...


def deployment_output_checker(deploy_target_bucket: str, bundle_name: str,
                              deploy_name: str, resources: dict,
                              succeeded: bool = True,
                              prefix: Optional[str] = None,
                              suffix: Optional[str] = None, **kwargs):
    results = {}
    missing_resources = []

    if succeeded:
        output_path = f'{bundle_name}/{DEPLOY_OUTPUT_DIR}/{deploy_name}.json'
    else:
        output_path = \
            f'{bundle_name}/{DEPLOY_OUTPUT_DIR}/{deploy_name}_failed.json'

    output = get_s3_bucket_file_content(deploy_target_bucket, output_path)
    redundant_resources = copy.deepcopy(output)

    for res_name, res_type in resources.items():
        if prefix:
            res_name = prefix + res_name
        if suffix:
            res_name = res_name + suffix
        is_res_present = False
        for arn, meta in output.items():
            if res_name == meta['resource_name']:
                redundant_resources.pop(arn)
                is_res_present = True
                break
        if not is_res_present:
            missing_resources.append({res_name: res_type})

    if missing_resources:
        results['missing_resources'] = missing_resources

    if redundant_resources:
        results['redundant_resources'] = redundant_resources

    return results if results else True


def resource_existence(resources: dict, suffix: Optional[str] = None,
                       prefix: Optional[str] = None, **kwargs):
    ...


# ------------ Modification Handlers -------------
def policy_modification(resource_name: str, update_time: str | datetime,
                        **kwargs):
    response = connections.get_iam_policy(resource_name)
    response_update_date = response.get('UpdateDate')
    if response_update_date and response_update_date >= update_time: # START of update time!!!
        return True


def lambda_modification(resource_name: str, update_time: str | datetime,
                        **kwargs):
    response = connections.get_function_configuration(resource_name)
    response_update_date = response.get('LastModified')
    if response_update_date and response_update_date >= update_time:
        return True


def lambda_layer_modification(resource_name: str, update_time: str | datetime,
                              **kwargs):
    response = connections.get_function_configuration(resource_name)
    response_update_date = response.get('LastModified')
    if response_update_date and response_update_date >= update_time:
        return True


# ------------ MAPPINGS -----------------

HANDLERS_MAPPING = {
    'exit_code': exit_code,
    'artifacts_existence': artifacts_existence,
    'build_meta': build_meta,
    'deployment_output': deployment_output_checker,
    'resource_existence': resource_existence
}


TYPE_MODIFICATION_FUNC_MAPPING = {
    'iam_policy': policy_modification,
    'iam_role': ...,
    'lambda': lambda_modification,
    'lambda_layer': lambda_layer_modification
}

