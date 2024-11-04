import copy
import json
from datetime import datetime
from typing import Optional

from tests.smoke.commons import connections
from tests.smoke.commons.connections import get_s3_bucket_file_content
from tests.smoke.commons.constants import DEPLOY_OUTPUT_DIR, \
    RESOURCE_TYPE_CONFIG_PARAM, BUNDLE_NAME, DEPLOY_NAME
from tests.smoke.commons.utils import find_max_version, deep_get


def exit_code_checker(actual_exit_code: int, expected_exit_code: int,
                      **kwargs):
    return actual_exit_code == expected_exit_code


def artifacts_existence_checker(artifacts_list: list,
                                deploy_target_bucket: str,
                                suffix: Optional[str] = None,
                                prefix: Optional[str] = None, **kwargs):
    missing_resources = []
    succeeded_deploy = kwargs.get('succeeded_deploy')
    for artifact in artifacts_list:
        if succeeded_deploy is not None:
            file_key = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{artifact}'
        else:
            file_key = f'{BUNDLE_NAME}/{artifact}'
        exist = connections.get_s3_bucket_object(
            bucket_name=deploy_target_bucket, file_key=file_key)
        if not exist:
            missing_resources.append(artifact)
    return {'missing_resources': missing_resources} \
        if missing_resources else True


def build_meta_checker(resources: dict, deploy_target_bucket: str, **kwargs):
    results = {}
    invalid_resources = []  # missing or invalid type
    build_meta_json = connections.get_s3_bucket_file_content(
        bucket_name=deploy_target_bucket,
        file_key=f'{BUNDLE_NAME}/build_meta.json')
    if not build_meta_json:
        return False

    build_meta_content = json.loads(build_meta_json)
    for resource_name, resource_type in resources.items():
        if not (resource_data := build_meta_content.pop(resource_name, {})):
            invalid_resources.append(resource_name)
            continue

        if resource_data.get('resource_type') != \
                resource_type.get('resource_type'):
            invalid_resources.append(resource_name)
            continue

    redundant_resources = list(build_meta_content.keys())

    if invalid_resources:
        results['invalid_resources'] = invalid_resources
    if redundant_resources:
        results['redundant_resources'] = redundant_resources

    return results if (invalid_resources or redundant_resources) else True


def deployment_output_checker(deploy_target_bucket: str, resources: dict,
                              succeeded_deploy: bool = True,
                              prefix: Optional[str] = None,
                              suffix: Optional[str] = None, **kwargs):
    results = {}
    missing_resources = []

    if succeeded_deploy:
        output_path = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}.json'
    else:
        output_path = \
            f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}_failed.json'

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

# ------------ Existence checkers -------------


def iam_policy_existence_checker(name: str) -> bool:
    return True if connections.get_iam_policy(name) else False


def iam_role_existence_checker(name: str) -> bool:
    return True if connections.get_iam_role(name) else False


def lambda_existence_checker(name: str) -> bool:
    return True if connections.get_function_configuration(name) else False


def lambda_layer_existence_checker(name: str) -> bool:
    return True if connections.get_layer_version(name) else False


def api_gateway_existence_checker(name: str) -> bool:
    return True if connections.get_api_gw_id(name) else False


def sqs_queue_existence_checker(name: str) -> bool:
    return True if connections.get_sqs_queue_url(name) else False


def sns_topic_existence_checker(name: str) -> bool:
    return True if connections.get_sns_topic_attributes(name) else False


def dynamo_db_existence_checker(name: str) -> bool:
    return True if connections.get_dynamodb_table_description(name) else False


def cw_rule_existence_checker(name: str) -> bool:
    return True if connections.get_event_bridge_rule(name) else False


def s3_bucket_existence_checker(name: str) -> bool:
    return True if connections.get_s3_bucket_head(name) else False


def cognito_idp_existence_checker(name: str) -> bool:
    return True if connections.get_cup_id(name) else False


def swagger_ui_existence_checker(name: str, deployment_bucket: str) -> bool:
    description = connections.describe_swagger_ui(
        name=name,
        deployment_bucket=deployment_bucket,
        bundle_name=BUNDLE_NAME,
        deploy_name=DEPLOY_NAME)
    if description:
        target_bucket = description.get('target_bucket', '')
        index_document = deep_get(description,
                                  ['website_hosting', 'index_document'])
        bucket_exist = connections.get_s3_bucket_head(target_bucket)
        web_site_config = connections.get_s3_bucket_website(name)
        index_doc_exists = connections.get_s3_bucket_object(target_bucket,
                                                            index_document)
        return True if all([bucket_exist, web_site_config, index_doc_exists]) \
            else False


# ------------ Modification Handlers -------------

def policy_modification_checker(resource_name: str,
                                update_time: str | datetime, **kwargs):
    response = connections.get_iam_policy(resource_name)
    response_update_date = response.get('Policy', {}).get('UpdateDate')
    if response_update_date and response_update_date.replace(
            tzinfo=None) >= update_time:
        return True


def lambda_modification_checker(resource_name: str,
                                update_time: str | datetime, **kwargs):
    response = connections.get_function_configuration(resource_name)
    if not response:
        return False
    response_update_date = response.get('LastModified')
    if response_update_date and datetime.strptime(
            response_update_date, '%Y-%m-%dT%H:%M:%S.%f%z').\
            replace(tzinfo=None) >= update_time:
        return True


def lambda_layer_modification_checker(resource_name: str,
                                      update_time: str | datetime, **kwargs):
    response = connections.get_layer_version(resource_name)
    layer_versions = response.get('LayerVersions')
    latest_version = find_max_version(layer_versions)
    response_update_date = latest_version.get('CreatedDate')
    if response_update_date and response_update_date >= update_time:
        return True


def outputs_modification_checker(deploy_target_bucket:str,
                                 update_time: str | datetime, **kwargs):
    response = connections.if_s3_object_modified(
        bucket_name=deploy_target_bucket,
        file_key=f'{BUNDLE_NAME}/outputs/{DEPLOY_NAME}.json',
        modified_since=update_time)
    if not response:
        return False
    return True


# ------------ MAPPINGS -----------------

TYPE_EXISTENCE_FUNC_MAPPING = {
    'iam_policy': iam_policy_existence_checker,
    'iam_role': iam_role_existence_checker,
    'lambda': lambda_existence_checker,
    'lambda_layer': lambda_layer_existence_checker,
    'api_gateway': api_gateway_existence_checker,
    'api_gateway_oas_v3': api_gateway_existence_checker,
    'sqs_queue': sqs_queue_existence_checker,
    'sns_topic': sns_topic_existence_checker,
    'dynamo_db': dynamo_db_existence_checker,
    'cw_rule': cw_rule_existence_checker,
    's3_bucket': s3_bucket_existence_checker,
    'cognito_idp': cognito_idp_existence_checker,
    'swagger_ui': swagger_ui_existence_checker
}

TYPE_MODIFICATION_FUNC_MAPPING = {
    'iam_policy': policy_modification_checker,
    'iam_role': ...,
    'lambda': lambda_modification_checker,
    'lambda_layer': lambda_layer_modification_checker
}


def resource_modification_checker(resources: dict, update_time: str,
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
    'exit_code': exit_code_checker,
    'artifacts_existence': artifacts_existence_checker,
    'build_meta': build_meta_checker,
    'deployment_output': deployment_output_checker,
    'resource_existence': resource_existence,
    'resource_modification': resource_modification_checker,
    'outputs_modification': outputs_modification_checker
}
