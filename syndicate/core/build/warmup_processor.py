import os

import boto3
import requests
from requests_aws_sign import AWSV4Sign

from syndicate.commons.log_helper import get_logger
from syndicate.core import ResourceProvider
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.conf.processor import ConfigHolder
from syndicate.core.helper import exit_on_exception

_LOG = get_logger('syndicate.core.build.warmup_processor')

NODEJS_RUNTIME = 'nodejs'
PYTHON_RUNTIME = 'python'

GET_METHOD = 'GET'
POST_METHOD = 'POST'
PUT_METHOD = 'PUT'
PATCH_METHOD = 'PATCH'
DELETE_METHOD = 'DELETE'

methods_check = {
    POST_METHOD: requests.post,
    GET_METHOD: requests.get,
    PUT_METHOD: requests.put,
    PATCH_METHOD: requests.patch,
    DELETE_METHOD: requests.delete
}


def process_api_gw_resources(paths_to_be_triggered,
                             resource_path_warmup_key_mapping):
    resource_method_mapping = {}
    resource_warmup_key_mapping = {}
    for api_gw_link, path_method_mapping in paths_to_be_triggered.items():
        for path, method in path_method_mapping.items():
            resource_link = api_gw_link + path
            resource_method_mapping.update({resource_link: method})
            resource_warmup_key_mapping.update(
                {resource_link: resource_path_warmup_key_mapping[api_gw_link]
                [path]})
    return resource_method_mapping, resource_warmup_key_mapping


def get_aws_sign():
    config = __get_config()

    boto3_session = boto3.session.Session()
    credentials = boto3_session.get_credentials()
    credentials.access_key = config.aws_access_key_id
    credentials.secret_key = config.aws_secret_access_key
    region = config.region

    service = 'execute-api'
    auth = AWSV4Sign(credentials, region, service)
    return auth


def warm_upper(resource_method_mapping, resource_warmup_key_mapping,
               lambda_auth, header_name, header_value):
    for uri, methods in resource_method_mapping.items():
        for method in methods:
            warmup_method = methods_check.get(method)
            warmup_key = resource_warmup_key_mapping[uri]
            params = {warmup_key: "true"}
            if lambda_auth:
                headers = {header_name: header_value}
                warmup_method(uri, headers=headers, params=params)
            else:
                auth = get_aws_sign()
                warmup_method(uri, auth=auth, params=params)


def _get_api_gw_client():
    return ResourceProvider.instance.api_gw().connection.client


def get_api_stage(rest_api_id, user_input_stage_name, echo):
    api_gw_client = _get_api_gw_client()
    stages_info = api_gw_client.get_stages(restApiId=rest_api_id)
    stages = stages_info.get('item')
    all_stage_names = [stage.get('stageName') for stage in stages]

    if not user_input_stage_name:
        if len(all_stage_names) == 1:
            stage_name = all_stage_names[0]
        else:
            echo(f'Stage name(s) for {rest_api_id} API ID: '
                 f'{", ".join(all_stage_names)}')
            stage_name = input('Select Stage from existing: ')
            if stage_name not in all_stage_names:
                raise AssertionError(f'Provided Stage name does not exists')

    else:
        if isinstance(user_input_stage_name, str):
            stage_name = [user_input_stage_name] \
                if user_input_stage_name in all_stage_names else None
        else:
            stage_name = [stage for stage in user_input_stage_name
                          if stage in all_stage_names]
        if not stage_name:
            raise AssertionError(
                f'Provided Stage name does not exists, available stage '
                f'name(s): {", ".join(all_stage_names)}')
        stage_name = stage_name[0]

    return stage_name


def get_warmup_param(allowed_path_warmup_key_mapping, api_gw_path, lambda_arn):
    lambda_client = ResourceProvider.instance.lambda_resource().lambda_conn. \
        client

    lambda_name = lambda_arn.split('function:')[-1]
    func_name = lambda_name.split('/')[0]

    lambda_meta = lambda_client.get_function(FunctionName=func_name)
    lambda_runtime = lambda_meta['Configuration']['Runtime']

    warmup_param = 'warmUp'
    if lambda_runtime.startswith(PYTHON_RUNTIME) or \
            lambda_runtime.startswith(NODEJS_RUNTIME):
        warmup_param = 'warm_up'

    allowed_path_warmup_key_mapping.update({api_gw_path: warmup_param})
    return allowed_path_warmup_key_mapping


def get_api_gw_resources(api_gw_client, rest_api_id):
    resource = api_gw_client.get_resources(
        restApiId=rest_api_id,
        limit=500
    )
    resource_items = resource['items']
    resource_items_id = {item['id']: item['resourceMethods']
                         for item in resource_items
                         if 'resourceMethods' in item}

    resource_items_path = {item['id']: item['path']
                           for item in resource_items}
    return resource_items_path, resource_items_id


def get_api_gw_integration(rest_api_id):
    api_gw_client = _get_api_gw_client()
    resource_items_path, resource_items_id = get_api_gw_resources(
        api_gw_client, rest_api_id)

    affected_lambda = []
    allowed_path_method_mapping = {}
    allowed_path_warmup_key_mapping = {}
    for resource_id, methods in resource_items_id.items():
        for method in methods:
            integration = api_gw_client.get_integration(restApiId=rest_api_id,
                                                        resourceId=resource_id,
                                                        httpMethod=method)

            api_gw_path = resource_items_path[resource_id]
            lambda_arn = integration.get('uri')
            if lambda_arn and lambda_arn not in affected_lambda:
                affected_lambda.append(lambda_arn)

                if not api_gw_path in allowed_path_method_mapping:
                    allowed_path_method_mapping.update({api_gw_path: [method]})
                else:
                    allowed_path_method_mapping[api_gw_path].append(method)

                get_warmup_param(allowed_path_warmup_key_mapping, api_gw_path,
                                 lambda_arn)

    return allowed_path_method_mapping, allowed_path_warmup_key_mapping


def __get_config():
    conf_path = os.environ.get('SDCT_CONF')
    config = ConfigHolder(conf_path)
    return config


def get_api_gw_link(rest_api_id, stage_name):
    api_gw_link_template = 'https://{rest_api_id}.execute-api.{region}.' \
                           'amazonaws.com/{stage_name}'

    config = __get_config()
    region = config.region
    api_gw_link = api_gw_link_template.format(rest_api_id=rest_api_id,
                                              region=region,
                                              stage_name=stage_name)
    return api_gw_link


@exit_on_exception
def process_deploy_resources(bundle_name, deploy_name):
    output = load_deploy_output(bundle_name, deploy_name)

    output = {key: value for key, value in output.items() if
              value['resource_meta'].get('resource_type') == 'api_gateway'}

    paths_to_be_triggered = {}
    resource_path_warmup_key_mapping = {}
    if not output:
        _LOG.warning('No resources to warmup, exiting')
        return paths_to_be_triggered, resource_path_warmup_key_mapping

    for resource_arn, meta in output.items():
        rest_api_id = resource_arn.split('/')[-1]
        stage_name = meta.get('resource_meta', {}).get('deploy_stage')

        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            handle_paths_to_be_triggered(rest_api_id=rest_api_id,
                                         stage_name=stage_name,
                                         paths_to_be_triggered=
                                         paths_to_be_triggered,
                                         resource_path_warmup_key_mapping=
                                         resource_path_warmup_key_mapping)
    return paths_to_be_triggered, resource_path_warmup_key_mapping


def process_inputted_api_gw_id(api_id, stage_name, echo):
    api_gw_client = _get_api_gw_client()
    all_apis = api_gw_client.get_rest_apis().get('items', {})

    allowed_id = [api['id'] for api in all_apis]

    paths_to_be_triggered = {}
    resource_path_warmup_key_mapping = {}

    for rest_api_id in api_id:
        if rest_api_id not in allowed_id:
            echo(f'Provided {rest_api_id} API ID does not exists')
            continue

        stage_name = get_api_stage(rest_api_id, stage_name, echo=echo)
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            handle_paths_to_be_triggered(rest_api_id=rest_api_id,
                                         stage_name=stage_name,
                                         paths_to_be_triggered=
                                         paths_to_be_triggered,
                                         resource_path_warmup_key_mapping=
                                         resource_path_warmup_key_mapping)
    return paths_to_be_triggered, resource_path_warmup_key_mapping


def process_existing_api_gw_id(stage_name, echo):
    api_gw_client = _get_api_gw_client()
    all_apis = api_gw_client.get_rest_apis().get('items', {})

    all_api_name = {api['name']: api['id'] for api in all_apis}

    echo(f'Existed API Gateway: {", ".join(all_api_name)}')
    user_input_id = input('Select API from existing (multiple names must be'
                          ' separated by commas): ')
    user_input_id = user_input_id.split(",")
    user_input_id = {user_id.strip() for user_id in user_input_id}

    if not user_input_id.issubset(all_api_name):
        raise AssertionError(
            f'Specify only allowed IDs: {", ".join(all_api_name)}')

    paths_to_be_triggered = {}
    resource_path_warmup_key_mapping = {}

    for api_name in user_input_id:
        rest_api_id = all_api_name[api_name]
        stage_name = get_api_stage(rest_api_id, stage_name, echo)
        handle_paths_to_be_triggered(rest_api_id, stage_name,
                                     paths_to_be_triggered,
                                     resource_path_warmup_key_mapping)
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            handle_paths_to_be_triggered(rest_api_id=rest_api_id,
                                         stage_name=stage_name,
                                         paths_to_be_triggered=
                                         paths_to_be_triggered,
                                         resource_path_warmup_key_mapping=
                                         resource_path_warmup_key_mapping)
    return paths_to_be_triggered, resource_path_warmup_key_mapping


def handle_paths_to_be_triggered(rest_api_id, stage_name,
                                 paths_to_be_triggered,
                                 resource_path_warmup_key_mapping):
    api_gw_link = get_api_gw_link(rest_api_id, stage_name)
    allowed_path_method_mapping, allowed_path_warmup_key_mapping = \
        get_api_gw_integration(rest_api_id)
    paths_to_be_triggered.update(
        {api_gw_link: allowed_path_method_mapping})
    resource_path_warmup_key_mapping.update(
        {api_gw_link: allowed_path_warmup_key_mapping})
    return paths_to_be_triggered, resource_path_warmup_key_mapping
