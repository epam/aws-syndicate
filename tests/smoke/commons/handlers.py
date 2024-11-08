import json
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from commons.checkers import TYPE_MODIFICATION_FUNC_MAPPING, \
    exit_code_checker, artifacts_existence_checker, deployment_output_checker, \
    build_meta_checker, TYPE_EXISTENCE_FUNC_MAPPING, lambda_triggers_checker, \
    outputs_modification_checker, TYPE_TAGS_FUNC_MAPPING
from commons.utils import populate_prefix_suffix
from commons import connections
from commons.constants import DEPLOY_OUTPUT_DIR, RESOURCE_TYPE_CONFIG_PARAM, \
    BUNDLE_NAME, DEPLOY_NAME, SWAGGER_UI_RESOURCE_TYPE, TAGS_CONFIG_PARAM, \
    API_GATEWAY_OAS_V3_RESOURCE_TYPE, LAMBDA_LAYER_RESOURCE_TYPE, \
    RESOURCE_NAME_CONFIG_PARAM


def exit_code_handler(actual_exit_code: int, expected_exit_code: int,
                      **kwargs):

    return True if exit_code_checker(actual_exit_code, expected_exit_code) \
        else {'expected_exit_code': expected_exit_code,
              'actual_exit_code': actual_exit_code}


def artifacts_existence_handler(artifacts_list: list,
                                deploy_target_bucket: str,
                                reverse_check: bool = False,
                                succeeded_deploy: Optional[bool] = None,
                                **kwargs):
    missing_resources = []
    for artifact in artifacts_list:
        if succeeded_deploy is not None:
            file_key = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{artifact}'
        else:
            file_key = f'{BUNDLE_NAME}/{artifact}'
        is_file_exists = artifacts_existence_checker(file_key,
                                                     deploy_target_bucket)
        if is_file_exists and reverse_check:
            missing_resources.append(artifact)
        elif not is_file_exists and not reverse_check:
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
                              reverse_check: bool = False,
                              prefix: Optional[str] = None,
                              suffix: Optional[str] = None, **kwargs):
    if succeeded_deploy:
        output_path = f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}.json'
    else:
        output_path = \
            f'{BUNDLE_NAME}/{DEPLOY_OUTPUT_DIR}/{DEPLOY_NAME}_failed.json'

    output = connections.get_s3_bucket_file_content(deploy_target_bucket,
                                                    output_path)
    output_json = json.loads(output)
    return deployment_output_checker(
        output_json,
        populate_prefix_suffix(resources, prefix, suffix),
        reverse_check=reverse_check)


def resource_existence_handler(resources: dict, deploy_target_bucket: str,
                               suffix: Optional[str] = None,
                               prefix: Optional[str] = None,
                               reverse_check: bool = False, **kwargs):
    results = {}
    resources = populate_prefix_suffix(resources, prefix, suffix)

    non_existent_resources = {}
    non_checked_resources = {}
    existent_resources = {}
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
        elif reverse_check:
            existent_resources[res_name] = res_meta

    if not reverse_check and non_existent_resources:
        results['non_existent_resources'] = non_existent_resources
    if non_checked_resources:
        results['non_checked_resources'] = non_checked_resources
    if reverse_check and existent_resources:
        results['existent_resources'] = existent_resources

    return results if any(results.values()) else True


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


def outputs_modification_handler(deploy_target_bucket: str,
                                 update_time: str | datetime,
                                 succeeded_deploy: bool = True, **kwargs):
    return True if outputs_modification_checker(deploy_target_bucket,
                                                update_time,
                                                succeeded_deploy) else False


def tag_existence_handler(resources: dict,
                          suffix: Optional[str] = None,
                          prefix: Optional[str] = None,
                          reverse_check: bool = False, **kwargs):
    results = {}
    resources = populate_prefix_suffix(resources, prefix, suffix)

    missing_tags = {}
    redundant_tags = {}
    for res_name, res_meta in resources.items():
        res_type = res_meta[RESOURCE_TYPE_CONFIG_PARAM]

        if res_meta.get(TAGS_CONFIG_PARAM)\
                and res_type not in (SWAGGER_UI_RESOURCE_TYPE,
                                     API_GATEWAY_OAS_V3_RESOURCE_TYPE,
                                     LAMBDA_LAYER_RESOURCE_TYPE):
            tag_func = TYPE_TAGS_FUNC_MAPPING.get(res_type)
            if not tag_func:
                print(f'Unknown resource type `{res_type}`. Cannot list tags.')
                missing_tags[res_name] = res_type
                continue
            missing = tag_func(res_name, res_meta[TAGS_CONFIG_PARAM])
            if missing is not True and reverse_check:
                continue
            elif missing is True and reverse_check:
                redundant_tags[res_name] = res_meta[TAGS_CONFIG_PARAM]
            elif missing is not True:
                missing_tags[res_name] = missing

    if missing_tags:
        results['missing_tags'] = missing_tags
    if redundant_tags:
        results['redundant_tags'] = redundant_tags

    return results if any(results.values()) else True


def lambda_trigger_handler(triggers: dict, suffix: Optional[str] = None,
                           prefix: Optional[str] = None,
                           alias: Optional[str] = None,
                           **kwargs) -> bool | dict:
    invalid_lambdas = {}
    for lambda_name, triggers_meta in triggers.items():
        if prefix:
            lambda_name = prefix + lambda_name
        if suffix:
            lambda_name = lambda_name + suffix
        if alias:
            lambda_name = lambda_name + f':{alias}'

        for trigger in triggers_meta:
            trigger_name = trigger[RESOURCE_NAME_CONFIG_PARAM]
            if prefix:
                trigger_name = prefix + trigger_name
            if suffix:
                trigger_name = trigger_name + suffix
            trigger[RESOURCE_NAME_CONFIG_PARAM] = trigger_name

        response = lambda_triggers_checker(lambda_name, triggers_meta)
        if response:
            invalid_lambdas[lambda_name] = response

    return invalid_lambdas if invalid_lambdas else True


HANDLERS_MAPPING = {
    'exit_code': exit_code_handler,
    'artifacts_existence': artifacts_existence_handler,
    'build_meta': build_meta_handler,
    'deployment_output': deployment_output_handler,
    'resource_existence': resource_existence_handler,
    'resource_modification': resource_modification_handler,
    'outputs_modification': outputs_modification_handler,
    'tag_existence': tag_existence_handler,
    'lambda_trigger_existence': lambda_trigger_handler
}
