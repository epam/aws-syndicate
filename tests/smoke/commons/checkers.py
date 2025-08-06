import copy
from datetime import datetime
import sys
from pathlib import Path
from time import sleep
from typing import Optional

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from commons.constants import BUNDLE_NAME, DEPLOY_NAME, \
    RESOURCE_TYPE_CONFIG_PARAM, RESOURCE_NAME_CONFIG_PARAM, \
    RESOURCE_META_CONFIG_PARAM, UPDATED_BUNDLE_NAME
from commons.utils import deep_get, find_max_lambda_layer_version, \
    compare_dicts, read_syndicate_aliases
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
    for resource_name, resource_meta in resources.items():
        if not (resource_data := build_meta.pop(resource_name, {})):
            invalid_resources.append(resource_name)
            continue

        if resource_data.get('resource_type') != \
                resource_meta.get('resource_type'):
            invalid_resources.append(resource_name)
            continue

    redundant_resources = list(build_meta.keys())

    if invalid_resources:
        results['invalid_resources'] = invalid_resources
    if redundant_resources:
        results['redundant_resources'] = redundant_resources

    return results if results else True


def build_meta_content_checker(build_meta: dict, resources: dict):
    results = {}
    missing_tags = []
    redundant_tags = []
    missing_envs = []
    redundant_envs = []
    for resource_name, resource_meta in resources.items():
        if not (resource_data := build_meta.pop(resource_name, {})):
            continue

        if resource_data.get('resource_type') != \
                resource_meta.get('resource_type'):
            continue

        if (build_tags := resource_data.get('tags', {})) != \
                (meta_tags := resource_meta.get('tags', {})):
            missing_tags.append({
                resource_name: dict(set(meta_tags.items()) - set(build_tags.items()))})
            redundant_tags.append({
                resource_name: dict(set(build_tags.items()) - set(meta_tags.items()))})

        if (build_envs := resource_data.get('env_variables', {})) != \
                (meta_envs := resource_meta.get('env_variables', {})):
            for key, value in build_envs.items():
                if not meta_envs.get(key) or meta_envs[key] != value:
                    redundant_envs.append({resource_name: {key: value}})

            for key, value in meta_envs.items():
                if not build_envs.get(key) or build_envs[key] != value:
                    missing_envs.append({resource_name: {key: value}})

    if missing_tags:
        results['missing_tags'] = missing_tags
    if redundant_tags:
        results['redundant_tags'] = redundant_tags
    if missing_envs:
        results['missing_envs'] = missing_envs
    if redundant_envs:
        results['redundant_envs'] = redundant_envs

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


def lambda_triggers_checker(lambda_name: str, triggers: list) -> dict:
    result = {}
    missing_arns = []
    sqs_arn = 'arn:aws:sqs:{0}:{1}:{2}'
    sns_arn = 'arn:aws:sns:{0}:{1}:{2}'
    event_arn = 'arn:aws:events:{0}:{1}:rule/{2}'
    dynamodb_stream_arn = 'arn:aws:dynamodb:{0}:{1}:table/{2}/stream/'
    s3_bucket_arn = 'arn:aws:s3:::{0}'
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
            if not trigger_found:
                missing_arns.append(arn)

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] == 'sqs_queue':
            trigger_arn = sqs_arn.format(REGION, ACCOUNT_ID, trigger_name)
            events = connections.get_lambda_event_source_mappings(lambda_name)
            event_arns = set(event.get('EventSourceArn') for event in events)
            if trigger_arn not in event_arns:
                missing_arns.append(trigger_arn)

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] == 'dynamodb_trigger':
            trigger_arn = dynamodb_stream_arn.format(REGION, ACCOUNT_ID,
                                                     trigger_name)
            events = connections.get_lambda_event_source_mappings(lambda_name)
            for event in events:
                if event.get('EventSourceArn').startswith(trigger_arn):
                    trigger_found = True
                    break
            if not trigger_found:
                missing_arns.append(trigger_arn)

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] in (
                'cloudwatch_rule', 'eventbridge_rule'):
            arn = event_arn.format(REGION, ACCOUNT_ID, trigger_name)
            rule_targets = connections.get_event_bridge_rule_targets(trigger_name)
            for target in rule_targets:
                if lambda_name in target['Arn']:
                    trigger_found = True
                    break
            if not trigger_found:
                missing_arns.append(arn)

        elif trigger[RESOURCE_TYPE_CONFIG_PARAM] == 's3_trigger':
            s3_notification_config = \
                connections.get_bucket_notification_configuration(trigger_name)
            s3_lambda_func_config =  \
                s3_notification_config.get('LambdaFunctionConfigurations', [])
            act_lambda_arn = lambda_arn.format(REGION, ACCOUNT_ID,
                                               lambda_name)
            for s3_notification_config in s3_lambda_func_config:
                if act_lambda_arn in \
                        s3_notification_config['LambdaFunctionArn']:
                    trigger_found = True
                    break
            if not trigger_found:
                missing_arns.append(s3_bucket_arn.format(trigger_name))

    if missing_arns:
        result['missing_triggers'] = missing_arns

    return result


def lambda_envs_checker(lambda_name: str, envs: dict,
                        qualifier: str = None) -> dict:
    missing_envs = {}
    result = {}
    lambda_envs = connections.get_lambda_envs(lambda_name, qualifier).get(
        'Variables', {})

    for key, value in envs.items():
        if not lambda_envs.get(key) or (
                lambda_envs[key] != value and value != '*'):
            # extract value for alias placeholders like '${region}' or '*${region}*'
            aliases = read_syndicate_aliases() or {}
            for a_name, a_value in aliases.items():
                if '${' + a_name + '}' in value:
                    value = value.replace('${' + a_name + '}', a_value)

            if lambda_envs.get(key) == value:
                lambda_envs.pop(key)
                continue
            if '*' in value:
                if all(v in lambda_envs[key] for v in value.split('*')):
                    lambda_envs.pop(key)
                    continue

            missing_envs[key] = value
        else:
            lambda_envs.pop(key)

    if missing_envs:
        result['missing_envs'] = missing_envs
    if lambda_envs:
        result['redundant_envs'] = lambda_envs

    return result


def appsync_modification_checker(appsync_name: str,
                                 data_sources: list[dict],
                                 resolvers: list[dict],
                                 functions: Optional[list[dict]] = []) \
        -> dict | None:
    missing_sources = []
    missing_resolvers = []
    missing_functions = []
    result = {}

    api_id = connections.get_appsync_id(appsync_name)
    if not api_id:
        return
    actual_data_sources = connections.list_appsync_data_sources(api_id)
    actual_functions = connections.list_appsync_functions(api_id)

    for source in data_sources:
        break_loop = False
        for actual_source in actual_data_sources:
            if source['name'] == actual_source['name'] and \
                    source['type'] == actual_source['type']:
                actual_data_sources.remove(actual_source)
                break_loop = True
                break
        if not break_loop:
            missing_sources.append(source)
            break

    for func in functions:
        break_loop = False
        for actual_func in actual_functions:
            if func['name'] == actual_func['name'] and \
                    func['data_source_name'] == actual_func['dataSourceName']:
                actual_functions.remove(actual_func)
                break_loop = True
                break
        if not break_loop:
            missing_functions.append(func)
            break

    for res in resolvers:
        actual_resolvers = connections.list_appsync_resolvers(api_id,
                                                              res['type_name'])
        break_loop = False
        for actual_res in actual_resolvers:
            if res['type_name'] == actual_res['typeName'] and \
                    res['field_name'] == actual_res['fieldName'] and \
                    res['data_source_name'] == actual_res['dataSourceName']:
                actual_resolvers.remove(actual_res)
                break_loop = True
                break

        if not break_loop:
            missing_resolvers.append(res)
            break

        if actual_resolvers:
            result['redundant_resolvers'].extend([
                {'type_name': a['typeName'], 'field_name': a['fieldName'],
                 'data_source_name': a['dataSourceName']} for a in
                actual_resolvers
            ])

    if missing_sources:
        result['missing_sources'] = missing_sources
    if missing_resolvers:
        result['missing_resolvers'] = missing_resolvers
    if missing_functions:
        result['missing_functions'] = missing_functions
    if actual_data_sources:
        result['redundant_sources'] = [{'name': a['name'], 'type': a['type']}
                                       for a in actual_data_sources]

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


def swagger_ui_existence_checker(name: str, deployment_bucket: str,
                                 path: str = []) -> bool:
    description = connections.describe_swagger_ui(
        name=name,
        deployment_bucket=deployment_bucket,
        bundle_path='/'.join([*path, BUNDLE_NAME]),
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


def appsync_existence_checker(name: str) -> bool:
    return True if connections.get_appsync_id(name) else False


def batch_comp_env_existence_checker(name: str) -> bool:
    sleep(10)  # in case there was not enough time to delete completely
    return True if connections.get_batch_comp_env(name) else False


def batch_job_queue_existence_checker(name: str) -> bool:
    return True if connections.get_batch_job_queue(name) else False


def batch_job_def_existence_checker(name: str) -> bool:
    return True if connections.get_batch_job_definition(name) else False


def step_function_existence_checker(name: str) -> bool:
    return True if connections.get_step_functions(name) else False


def cloudwatch_alarm_existence_checker(name: str) -> bool:
    return True if connections.get_cw_alarm(name) else False


def web_socket_api_gateway_existence_checker(name: str) -> bool:
    return True if connections.get_web_socket_api_gateway(name) else False


def rds_db_cluster_existence_checker(name: str) -> bool:
    return True if connections.get_rds_db_cluster(name) else False


def rds_db_instance_existence_checker(instance_name: str,
                                      cluster_name: str) -> bool:
    return True if connections.get_rds_db_instance(instance_name,
                                                   cluster_name) else False


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


def appsync_tags_checker(name: str, tags: list) -> dict | bool:
    received_tags = connections.list_appsync_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def batch_comp_env_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_batch_comp_env(name)
    if not arn:
        return False
    received_tags = connections.list_batch_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def batch_job_queue_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_batch_job_queue(name)
    if not arn:
        return False
    received_tags = connections.list_batch_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def batch_job_definition_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_batch_job_definition(name)
    if not arn:
        return False
    received_tags = connections.list_batch_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def step_function_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_step_functions(name)
    if not arn:
        return False
    received_tags = connections.list_step_function_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def cloudwatch_alarm_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_cw_alarm(name)
    if not arn:
        return False
    received_tags = connections.list_cw_alarm_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def web_socket_api_gateway_tags_checker(name: str, tags: list) -> dict | bool:
    arn = connections.get_web_socket_api_gateway(name)
    if not arn:
        return False
    received_tags = connections.list_web_socket_api_gateway_tags(arn, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def rds_db_cluster_tags_checker(name: str, tags: dict) -> dict | bool:
    received_tags = connections.list_rds_db_cluster_tags(name, tags)
    if missing_tags := compare_dicts(received_tags, tags):
        return dict(missing_tags)
    return True


def rds_db_instance_tags_checker(instance_name: str,
                                 cluster_name: str, tags: dict) -> dict | bool:
    received_tags = connections.list_rds_db_instance_tags(instance_name,
                                                          cluster_name, tags)
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
    'swagger_ui': swagger_ui_existence_checker,
    'appsync': appsync_existence_checker,
    'batch_compenv': batch_comp_env_existence_checker,
    'batch_jobqueue': batch_job_queue_existence_checker,
    'batch_jobdef': batch_job_def_existence_checker,
    'web_socket_api_gateway': web_socket_api_gateway_existence_checker,
    'step_functions': step_function_existence_checker,
    'cloudwatch_alarm': cloudwatch_alarm_existence_checker,
    'rds_db_cluster': rds_db_cluster_existence_checker,
    'rds_db_instance': rds_db_instance_existence_checker
}


TYPE_MODIFICATION_FUNC_MAPPING = {
    'iam_policy': policy_modification_checker,
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
    'cognito_idp': cognito_idp_tags_checker,
    'appsync': appsync_tags_checker,
    'batch_compenv': batch_comp_env_tags_checker,
    'batch_jobqueue': batch_job_queue_tags_checker,
    'batch_jobdef': batch_job_definition_tags_checker,
    'web_socket_api_gateway': web_socket_api_gateway_tags_checker,
    'step_functions': step_function_tags_checker,
    'cloudwatch_alarm': cloudwatch_alarm_tags_checker,
    'rds_db_cluster': rds_db_cluster_tags_checker,
    'rds_db_instance': rds_db_instance_tags_checker
}
