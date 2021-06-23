import json
import schemathesis
import boto3
import requests
import os
import click

from syndicate.commons.log_helper import get_logger
from syndicate.core import ResourceProvider
from syndicate.core.conf.processor import ConfigHolder
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.build.deployment_processor import _filter_the_dict
from syndicate.core.helper import exit_on_exception
from requests_aws_sign import AWSV4Sign


_LOG = get_logger('syndicate.core.build.warmup_processor')

ANY_METHOD = 'x-amazon-apigateway-any-method'
GET_METHOD = 'get'
POST_METHOD = 'post'
PUT_METHOD = 'put'
PATCH_METHOD = 'patch'
DELETE_METHOD = 'delete'
OPTIONS_METHOD = 'options'

methods_check = {
    POST_METHOD: requests.post,
    GET_METHOD: requests.get,
    PUT_METHOD: requests.put,
    PATCH_METHOD: requests.patch,
    DELETE_METHOD: requests.delete
}


def process_schemas(schemas_list, paths_to_be_triggered=None):
    uri_method_dict = dict()
    for schema in schemas_list:
        url = schema.base_url.replace(schema.base_path[:-1],
                                      schema.base_path[1:-1])
        resources = schema.operations
        for resource, definition in resources.items():
            resource_url = url + resource
            for api_gw_id, paths in paths_to_be_triggered.items():
                if api_gw_id in url:
                    for path in paths:
                        if not resource_url.endswith(path):
                            continue
                        if resource_url not in uri_method_dict:
                            uri_method_dict.update({resource_url: [
                                each_path.lower() for each_path in
                                paths[path]]})
                        elif resource_url in uri_method_dict:
                            uri_method_dict[resource_url].append(
                                each_path.lower() for each_path in paths[path])
    return uri_method_dict


def get_aws_sign():
    CONF_PATH = os.environ.get('SDCT_CONF')
    CONFIG = ConfigHolder(CONF_PATH)
    region = CONFIG.region
    boto3_session = boto3.session.Session()
    credentials = boto3_session.get_credentials()
    credentials.access_key = CONFIG.aws_access_key_id
    credentials.secret_key = CONFIG.aws_secret_access_key
    service = 'execute-api'
    auth = AWSV4Sign(credentials, region, service)
    return auth


def lambda_auth_warm_up(warmup_method, uri, header_name, header_value):
    params = {"warm_up": "true"}
    headers = {header_name: header_value}
    warmup_method(uri, headers=headers, params=params)


def aws_iam_warm_up(warmup_method, uri):
    auth = get_aws_sign()
    headers = {"Content-Type": "application/json"}
    params = {"warm_up": "true"}
    warmup_method(uri, auth=auth, headers=headers, params=params)


def warm_upper(uri_method_dict, lambda_auth, header_name, header_value):
    for uri, methods in uri_method_dict.items():
        for method in methods:
            warmup_method = methods_check.get(method)
            if lambda_auth:
                lambda_auth_warm_up(warmup_method, uri, header_name,
                                    header_value)
            else:
                aws_iam_warm_up(warmup_method, uri)


def _get_api_gw_client():
    return ResourceProvider.instance.api_gw().connection.client


def _replace_method_any(schema_file):
    paths = schema_file.get('paths')
    for resource in paths:
        if ANY_METHOD in paths[resource].keys():
            paths[resource]['get'] = paths[resource].pop(ANY_METHOD)
    return schema_file


def transform_to_schema(exported_schema):
    file_schema = json.loads(exported_schema['body'].read())
    file_schema = _replace_method_any(file_schema)
    schema = schemathesis.from_file(str(file_schema),
                                    base_url=find_api_url(file_schema))
    return schema


def get_api_gw_export(rest_api_id, stage_name):
    api_gw_client = _get_api_gw_client()
    exported_schema = api_gw_client.get_export(
        restApiId=rest_api_id,
        stageName=stage_name,
        exportType='oas30',
        accepts='application/json')
    return exported_schema


def process_existed_api_gw_id(stage_name):
    api_gw_client = _get_api_gw_client()
    all_apis = api_gw_client.get_rest_apis().get('items', {})

    allowed_api_name = {}
    all_api_name = {}
    for api in all_apis:
        rest_api_id = api['id']
        rest_api_name = api['name']
        all_api_name.update({rest_api_name: rest_api_id})

    click.echo(f'Existed API Gateway: {", ".join(all_api_name)}')
    user_input_id = input('Select API from existing (multiple names must be'
                          ' separated by commas): ')
    user_input_id = user_input_id.split(",")

    schemas_list = []
    paths_to_be_triggered = {}
    for user_input in user_input_id:
        user_input = user_input.strip()
        if user_input not in all_api_name:
            raise AssertionError(
                f'Specify only allowed IDs: {", ".join(allowed_api_name)}')

        allowed_api_id = get_api_stages(all_api_name[user_input], stage_name)

        for id, api_gw_meta in allowed_api_id.items():
            for meta in api_gw_meta:
                paths_to_be_triggered.update({id: get_api_gw_integration(id)})
                schema = transform_to_schema(meta)
                schemas_list.append(schema)
    return schemas_list, paths_to_be_triggered


def get_api_stages(rest_api_id, user_input_stage_name):
    api_gw_client = _get_api_gw_client()
    stages_info = api_gw_client.get_stages(restApiId=rest_api_id)
    stages = stages_info.get('item')
    all_stage_names = [stage.get('stageName') for stage in stages]

    if not user_input_stage_name:
        if len(all_stage_names) == 1:
            stage_name = all_stage_names[0]
        else:
            click.echo(f'Stage name(s) for {rest_api_id} API ID: '
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

    allowed_api_id = {}
    exported_schema = get_api_gw_export(rest_api_id, stage_name)
    allowed_api_id.update({rest_api_id: [exported_schema]})
    return allowed_api_id


def get_api_gw_integration(rest_api_id):
    api_gw_client = _get_api_gw_client()

    resource = api_gw_client.get_resources(
        restApiId=rest_api_id
    )
    resource_items = resource['items']
    resource_items_id = {item['id']: item['resourceMethods']
                         for item in resource_items
                         if 'resourceMethods' in item}

    resource_items_path = {item['id']: item['path']
                           for item in resource_items}

    affected_lambda = []
    allowed_path_method = {}
    for resource_id, methods in resource_items_id.items():
        for method in methods:
            integration = api_gw_client.get_integration(restApiId=rest_api_id,
                                                        resourceId=resource_id,
                                                        httpMethod=method)
            if 'uri' in integration:
                lambda_uri = integration['uri']
                if lambda_uri not in affected_lambda:
                    affected_lambda.append(lambda_uri)
                    api_gw_path = resource_items_path[resource_id]
                    if not api_gw_path in allowed_path_method:
                        allowed_path_method.update({api_gw_path: [method]})
                    else:
                        allowed_path_method[api_gw_path].append(method)
    return allowed_path_method


def process_inputted_api_gw_id(api_id, stage_name):
    api_gw_client = _get_api_gw_client()
    all_apis = api_gw_client.get_rest_apis().get('items', {})

    allowed_id = []
    for api in all_apis:
        allowed_id.append(api['id'])

    schemas_list = []
    paths_to_be_triggered = {}
    for rest_api_id in api_id:
        if rest_api_id not in allowed_id:
            click.echo(f'Provided {rest_api_id} API ID does not exists')
            continue

        allowed_api_id = get_api_stages(rest_api_id, stage_name)
        for id, api_gw_meta in allowed_api_id.items():
            for meta in api_gw_meta:
                paths_to_be_triggered.update({id: get_api_gw_integration(id)})
                schema = transform_to_schema(meta)
                schemas_list.append(schema)
    return schemas_list, paths_to_be_triggered


def load_schema(api_gw_resources_meta):
    schemas = []
    paths_to_be_triggered = {}
    for resource_arn, meta in api_gw_resources_meta.items():
        rest_api_id = resource_arn.split('/')[-1]
        stage_name = meta.get('resource_meta', {}).get('deploy_stage')

        exported_schema = get_api_gw_export(rest_api_id, stage_name)
        paths_to_be_triggered.update(
            {rest_api_id: get_api_gw_integration(rest_api_id)}
        )
        schema = transform_to_schema(exported_schema)
        schemas.append(schema)
    return schemas, paths_to_be_triggered


@exit_on_exception
def warmup_resources(bundle_name, deploy_name):
    output = load_deploy_output(bundle_name, deploy_name)

    filters = [
        lambda v: v['resource_meta'].get('resource_type') == 'api_gateway'
    ]

    for function in filters:
        output = _filter_the_dict(dictionary=output, callback=function)

    if not output:
        _LOG.warning('No resources to warmup, exiting')
        return

    schemas = load_schema(api_gw_resources_meta=output)
    return schemas


def find_api_url(schema_doc):
    server = schema_doc['servers'][0]
    api_base_path = server['variables']['basePath']['default']
    url = server['url'].format(basePath=api_base_path)
    return url
