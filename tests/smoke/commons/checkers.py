import copy
from datetime import datetime

from smoke.commons.constants import BUNDLE_NAME, DEPLOY_NAME
from smoke.commons.utils import deep_get, find_max_lambda_layer_version
from tests.smoke.commons import connections


def exit_code_checker(actual_exit_code: int, expected_exit_code: int,
                      **kwargs) -> bool:
    return actual_exit_code == expected_exit_code


def artifacts_existence_checker(artifact: str,
                                deploy_target_bucket: str) -> bool:
    return True if connections.get_s3_bucket_object(
            bucket_name=deploy_target_bucket, file_key=artifact) else False


def deployment_output_checker(output: dict, resources: dict) -> dict:
    results = {}
    missing_resources = {}

    redundant_resources = copy.deepcopy(output)

    for res_name, res_type in resources.items():
        is_res_present = False
        for arn, meta in output.items():
            if res_name == meta['resource_name']:
                redundant_resources.pop(arn)
                is_res_present = True
                break
        if not is_res_present:
            missing_resources.update({res_name: res_type})

    if missing_resources:
        results['missing_resources'] = missing_resources

    if redundant_resources:
        results['redundant_resources'] = redundant_resources

    return results if results else True


# ------------ Resource existence checkers -------------


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


# ------------ Resource modification checkers -------------

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
    latest_version = find_max_lambda_layer_version(layer_versions)
    response_update_date = latest_version.get('CreatedDate')
    if response_update_date and response_update_date >= update_time:
        return True


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
