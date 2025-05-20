import json
from typing import Optional
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from commons.checkers import exit_code_checker, artifacts_existence_checker, \
    TYPE_MODIFICATION_FUNC_MAPPING, deployment_output_checker, \
    build_meta_checker, TYPE_EXISTENCE_FUNC_MAPPING, lambda_triggers_checker, \
    lambda_envs_checker, build_meta_content_checker, TYPE_TAGS_FUNC_MAPPING, \
    appsync_modification_checker
from commons.utils import populate_resources_prefix_suffix, \
    read_syndicate_aliases, populate_prefix_suffix, split_deploy_bucket_path
from commons import connections
from commons.constants import DEPLOY_OUTPUT_DIR, RESOURCE_TYPE_CONFIG_PARAM, \
    BUNDLE_NAME, DEPLOY_NAME, SWAGGER_UI_RESOURCE_TYPE, TAGS_CONFIG_PARAM, \
    API_GATEWAY_OAS_V3_RESOURCE_TYPE, LAMBDA_LAYER_RESOURCE_TYPE, \
    RESOURCE_NAME_CONFIG_PARAM, UPDATED_BUNDLE_NAME, \
    RDS_DB_INSTANCE_RESOURCE_TYPE


def exit_code_handler(actual_exit_code: int, expected_exit_code: int,
                      **kwargs):

    return True if exit_code_checker(actual_exit_code, expected_exit_code) \
        else {'expected_exit_code': expected_exit_code,
              'actual_exit_code': actual_exit_code}


def artifacts_existence_handler(artifacts_list: list,
                                deploy_target_bucket: str,
                                reverse_check: bool = False,
                                succeeded_deploy: Optional[bool] = None,
                                update: Optional[bool] = None,
                                **kwargs):
    deploy_bucket, path = split_deploy_bucket_path(deploy_target_bucket)
    bundle_dir = UPDATED_BUNDLE_NAME if update else BUNDLE_NAME
    missing_resources = []
    for artifact in artifacts_list:
        if succeeded_deploy is not None:
            file_key = '/'.join([
                *path, bundle_dir, DEPLOY_OUTPUT_DIR, artifact
            ])
        else:
            file_key = '/'.join([*path, bundle_dir, artifact])
        is_file_exists = artifacts_existence_checker(file_key,
                                                     deploy_bucket)
        if is_file_exists and reverse_check:
            missing_resources.append(artifact)
        elif not is_file_exists and not reverse_check:
            missing_resources.append(artifact)
    return {'missing_resources': missing_resources} \
        if missing_resources else True


def build_meta_handler(resources: dict, deploy_target_bucket: str, **kwargs):
    deploy_bucket, path = split_deploy_bucket_path(deploy_target_bucket)
    file_key = '/'.join([*path, BUNDLE_NAME, 'build_meta.json'])
    build_meta = connections.get_s3_bucket_file_content(
        bucket_name=deploy_bucket, file_key=file_key)
    if not build_meta:
        return False

    build_meta_json = json.loads(build_meta)

    return build_meta_checker(build_meta_json, resources)


def build_meta_content_handler(resources: dict, deploy_target_bucket: str,
                               **kwargs):
    deploy_bucket, path = split_deploy_bucket_path(deploy_target_bucket)
    file_key = '/'.join([*path, BUNDLE_NAME, 'build_meta.json'])
    build_meta = connections.get_s3_bucket_file_content(
        bucket_name=deploy_bucket,
        file_key=file_key)
    if not build_meta:
        return False

    build_meta_json = json.loads(build_meta)

    return build_meta_content_checker(build_meta_json, resources)


def deployment_output_handler(deploy_target_bucket: str, resources: dict,
                              succeeded_deploy: bool = True,
                              reverse_check: bool = False,
                              prefix: Optional[str] = None,
                              suffix: Optional[str] = None,
                              update: Optional[bool] = False, **kwargs):
    deploy_bucket, path = split_deploy_bucket_path(deploy_target_bucket)
    bundle_dir = UPDATED_BUNDLE_NAME if update else BUNDLE_NAME
    output_path = '/'.join([*path, bundle_dir, DEPLOY_OUTPUT_DIR, DEPLOY_NAME])
    if succeeded_deploy:
        output_path += '.json'
    else:
        output_path += '_failed.json'

    output = connections.get_s3_bucket_file_content(deploy_bucket,
                                                    output_path)
    output_json = json.loads(output)
    return deployment_output_checker(
        output_json,
        populate_resources_prefix_suffix(resources, prefix, suffix),
        reverse_check=reverse_check)


def resource_existence_handler(resources: dict, deploy_target_bucket: str,
                               suffix: Optional[str] = None,
                               prefix: Optional[str] = None,
                               reverse_check: bool = False, **kwargs):
    results = {}
    resources = populate_resources_prefix_suffix(resources, prefix, suffix)

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
            deploy_bucket, path = split_deploy_bucket_path(deploy_target_bucket)
            is_exist = func(res_name, deploy_bucket, path)
        elif res_type == RDS_DB_INSTANCE_RESOURCE_TYPE:
            is_exist = func(res_name, res_meta.get('d_b_cluster_identifier'))
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


def tag_existence_handler(resources: dict,
                          suffix: Optional[str] = None,
                          prefix: Optional[str] = None,
                          reverse_check: bool = False, **kwargs):
    results = {}
    resources = populate_resources_prefix_suffix(resources, prefix, suffix)

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
            if res_type == RDS_DB_INSTANCE_RESOURCE_TYPE:
                missing = tag_func(res_name,
                                   res_meta.get('d_b_cluster_identifier'),
                                   res_meta[TAGS_CONFIG_PARAM])
            else:
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
                           **kwargs) -> bool | dict:
    invalid_lambdas = {}
    alias = read_syndicate_aliases().get('lambdas_alias_name')
    for lambda_name, triggers_meta in triggers.items():
        lambda_name = populate_prefix_suffix(lambda_name, prefix, suffix)
        if alias:
            lambda_name += f':{alias}'

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


def lambda_env_handler(env_variables: dict,
                       suffix: Optional[str] = None,
                       prefix: Optional[str] = None,
                       alias: Optional[str] = None, **kwargs) -> bool | dict:
    invalid_envs = {}
    for lambda_name, envs in env_variables.items():
        lambda_name = populate_prefix_suffix(lambda_name, prefix, suffix)
        if result := lambda_envs_checker(lambda_name, envs, qualifier=alias):
            invalid_envs[lambda_name] = result

    return invalid_envs if invalid_envs else True


def appsync_modification_handler(resources: dict,
                                 suffix: Optional[str] = None,
                                 prefix: Optional[str] = None,
                                 **kwargs) -> bool | dict:
    invalid_conf = {}
    for appsync_name, config in resources.items():
        appsync_name = populate_prefix_suffix(appsync_name, prefix, suffix)
        if result := appsync_modification_checker(appsync_name, **config):
            invalid_conf[appsync_name] = result

    return invalid_conf if invalid_conf else True


HANDLERS_MAPPING = {
    'exit_code': exit_code_handler,
    'artifacts_existence': artifacts_existence_handler,
    'build_meta': build_meta_handler,
    'build_meta_content': build_meta_content_handler,
    'deployment_output': deployment_output_handler,
    'resource_existence': resource_existence_handler,
    'resource_modification': resource_modification_handler,
    'tag_existence': tag_existence_handler,
    'lambda_trigger_existence': lambda_trigger_handler,
    'lambda_env_existence': lambda_env_handler,
    'appsync_modification': appsync_modification_handler
}
