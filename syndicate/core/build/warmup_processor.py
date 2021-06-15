import json
import schemathesis
import boto3
import requests
from requests_aws_sign import AWSV4Sign
import os

from syndicate.commons.log_helper import get_logger
from syndicate.core import ResourceProvider
from syndicate.core.build.bundle_processor import (create_deploy_output,
                                                   load_deploy_output,
                                                   load_failed_deploy_output,
                                                   load_meta_resources,
                                                   remove_deploy_output,
                                                   remove_failed_deploy_output)
from syndicate.core.build.deployment_processor import _filter_the_dict
from syndicate.core.helper import exit_on_exception
from hypothesis import settings

_LOG = get_logger('syndicate.core.build.warmup_processor')

ANY_METHOD = 'x-amazon-apigateway-any-method'


def _get_api_gw_client():
    return ResourceProvider.instance.api_gw().connection.client


def _replace_method_any(schema_file):
    paths = schema_file.get('paths')
    for resource in paths:
        if ANY_METHOD in paths[resource].keys():
            paths[resource]['get'] = paths[resource].pop(ANY_METHOD)
    return schema_file


def load_schema(api_gw_resources_meta):
    api_gw_client = _get_api_gw_client()
    schemes = []
    for resource_arn, meta in api_gw_resources_meta.items():
        api_id = resource_arn.split('/')[-1]
        stage_name = meta.get('resource_meta', {}).get('deploy_stage')

        exported_schema = api_gw_client.get_export(
            restApiId=api_id,
            stageName=stage_name,
            exportType='oas30',
            accepts='application/json')

        file_schema = json.loads(exported_schema['body'].read())
        file_schema = _replace_method_any(file_schema)
        schemes.append(file_schema)
    return schemes


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

    schemes = load_schema(api_gw_resources_meta=output)
    return schemes


def find_api_url(schema_doc):
    server = schema_doc['servers'][0]
    api_base_path = server['variables']['basePath']['default']
    url = server['url'].format(basePath=api_base_path)
    return url


def get_dir():
    return os.path.abspath(__file__)


def load_schema_file():
    warmup_dir = get_dir()
    warmup_schema_dir = warmup_dir.split(os.sep)[:-1]
    warmup_schema_file = os.path.join('/', *warmup_schema_dir,
                                      'schema.json')
    with open(warmup_schema_file) as f:
        schema = json.load(f)
    return schema


def get_requests_session():
    boto3_session = boto3.session.Session()
    credentials = boto3_session.get_credentials()
    region = boto3_session.region_name
    requests_session = requests.Session()
    requests_session.auth = AWSV4Sign(credentials, region, 'execute-api')
    return requests_session


schema = load_schema_file()
schema = schemathesis.from_file(str(schema),
                                base_url=find_api_url(schema))


@settings(max_examples=1, deadline=None)
@schema.parametrize(method=['GET', 'POST'])
def test_api(case):
    requests_session = get_requests_session()

    if '/download/{file+}' in case.path:
        return

    case.query = {'warmUp': 'true'}
    response = case.call(session=requests_session)
    print("{:4} {:<40} status: {:<3}, time: {:5.2f}s".format(
        case.method, case.path, response.status_code,
        response.elapsed.total_seconds()))