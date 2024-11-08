import copy
from datetime import datetime
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from commons.constants import BUNDLE_NAME, DEPLOY_NAME, \
    RESOURCE_TYPE_CONFIG_PARAM, RESOURCE_NAME_CONFIG_PARAM, \
    RESOURCE_META_CONFIG_PARAM
from commons.utils import deep_get, find_max_lambda_layer_version, \
    compare_dicts
from commons import connections
from commons.connections import REGION, ACCOUNT_ID


def exit_code_checker(actual_exit_code: int, expected_exit_code: int,
                      **kwargs) -> bool:
    return actual_exit_code == expected_exit_code


def artifacts_existence_checker(artifact: str,
                                deploy_target_bucket: str) -> bool:
    return True if connections.get_s3_bucket_object(
            bucket_name=deploy_target_bucket, file_key=artifact) else False


def build_meta_checker(build_meta: dict, resources: dict):
    results = {}
    invalid_resources = []  # missing or invalid type
    invalid_tags = []
    for resource_name, resource_meta in resources.items():
        if not (resource_data := build_meta.pop(resource_name, {})):
            invalid_resources.append(resource_name)
            continue

        if resource_data.get('resource_type') != \
                resource_meta.get('resource_type'):
            invalid_resources.append(resource_name)
            continue

        if resource_data.get('tags', {}) != resource_meta.get('tags', {}):
            invalid_tags.append({resource_name: resource_data.get('tags', {})})

    redundant_resources = list(build_meta.keys())

    if invalid_resources:
        results['invalid_resources'] = invalid_resources
    if redundant_resources:
        results['redundant_resources'] = redundant_resources
    if invalid_tags:
        results['invalid_tags'] = invalid_tags

    return results if results else True


def deployment_output_checker(output: dict, resources: dict,
                              reverse_check: bool) -> dict:
    results = {}
    not_passed_check_resources = {}

    redundant_resources = copy.deepcopy(output)

    for res_name, res_type in resources.items():
        is_res_present = False
        for arn, meta in output.items():
            if res_name == meta[RESOURCE_NAME_CONFIG_PARAM]:
                redundant_resources.pop(arn)
                is_res_present = True
                break
        if not is_res_present and not reverse_check:
            not_passed_check_resources.update({res_name: res_type})
        elif is_res_present and reverse_check:
            not_passed_check_resources.update({res_name: res_type})

    if not_passed_check_resources:
        if not reverse_check:
            results['missing_resources'] = not_passed_check_resources
        else:
            results['redundant_resources'] = not_passed_check_resources

    redundant_resource_info = {}
    for _, meta in redundant_resources.items():
        res_name = meta[RESOURCE_NAME_CONFIG_PARAM]
        res_type = meta[RESOURCE_META_CONFIG_PARAM][RESOURCE_TYPE_CONFIG_PARAM]
        redundant_resource_info[res_name] = res_type
    if redundant_resource_info and not reverse_check:
        results['redundant_resources'] = redundant_resource_info

    return results if results else True


def outputs_modification_checker(deploy_target_bucket: str,
                                 update_time: str | datetime,
                                 succeeded_deploy):
    if succeeded_deploy:
        file_key = f'{BUNDLE_NAME}/outputs/{DEPLOY_NAME}.json'
    else:
        file_key = f'{BUNDLE_NAME}/outputs/{DEPLOY_NAME}_failed.json'
    response = connections.if_s3_object_modified(
        bucket_name=deploy_target_bucket,
        file_key=file_key,
        modified_since=update_time)
    if not response:
        return False
    return True


def lambda_triggers_checker(lambda_name: str, triggers: list) -> dict:
    result = {}
    missing_arns = []
    redundant_arns = []
    sqs_arn = 'arn:aws:sqs:{0}:{1}:{2}'
    sns_arn = 'arn:aws:sns:{0}:{1}:{2}'
    event_arn = 'arn:aws:events:{0}:{1}:rule/{2}'
    lambda_arn = 'arn:aws:lambda:{0}:{1}:function:{2}'

    for trigger in triggers:
        trigger_found = False
        trigger_name = trigger[RESOURCE_NAME_CONFIG_PARAM]

        if trigger[RESOURCE_TYPE_CONFIG_PARAM] == 'sns_topic':
            arn = sns_arn.format(REGION, ACCOUNT_ID, trigger_name)
            topic_subscriptions = connections.get_sns_topic_subscriptions(arn)
            for subscription in topic_subscriptions:
                if subscription['Endpoint'] == lambda_arn.format(
                            REGION, ACCOUNT_ID, lambda_name):
                    trigger_found = True
                    break
            if trigger_found:
                continue

            missing_arns.append(arn)

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] == 'sqs_queue':
            trigger_arn = sqs_arn.format(REGION, ACCOUNT_ID, trigger_name)
            events = connections.get_lambda_event_source_mappings(lambda_name)
            event_arns = set(event.get('EventSourceArn') for event in events)
            if trigger_arn not in event_arns:
                missing_arns.append(trigger_arn)
            redundant_arns.extend(event_arns - {trigger_arn})

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] in (
                'cloudwatch_rule', 'eventbridge_rule'):
            arn = event_arn.format(REGION, ACCOUNT_ID, trigger_name)
            rule_targets = connections.get_event_bridge_rule_targets(trigger_name)
            for target in rule_targets:
                if lambda_name in target['Arn']:
                    trigger_found = True
                    break
            if trigger_found:
                continue

            missing_arns.append(arn)

    if missing_arns:
        result['missing_triggers'] = missing_arns
    if redundant_arns:
        result['redundant_triggers'] = redundant_arns

    return result

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
        web_site_config = connections.get_s3_bucket_website(target_bucket)
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
    latest_version = find_max_lambda_layer_version(response)
    response_update_date = latest_version.get('CreatedDate')
    if response_update_date and response_update_date >= update_time:
        return True


# -------------- Tags existence checkers ---------------

def iam_policy_tags_checker(name: str, tags: list) -> bool:
    received_tags = connections.list_policy_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return missing_tags
    return True


def iam_role_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_role_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def lambda_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_lambda_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def api_gateway_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_api_gateway_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def sqs_queue_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_sqs_queue_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def sns_topic_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_sns_topic_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def dynamo_db_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_dynamodb_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def cw_rule_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_event_bridge_rule_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def s3_bucket_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_s3_bucket_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def cognito_idp_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_cognito_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
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
    'dynamodb_table': dynamo_db_existence_checker,
    'cloudwatch_rule': cw_rule_existence_checker,
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


TYPE_TAGS_FUNC_MAPPING = {
    'iam_policy': iam_policy_tags_checker,
    'iam_role': iam_role_tags_checker,
    'lambda': lambda_tags_checker,
    'api_gateway': api_gateway_tags_checker,
    'sqs_queue': sqs_queue_tags_checker,
    'sns_topic': sns_topic_tags_checker,
    'dynamodb_table': dynamo_db_tags_checker,
    'cloudwatch_rule': cw_rule_tags_checker,
    's3_bucket': s3_bucket_tags_checker,
    'cognito_idp': cognito_idp_tags_checker
}
