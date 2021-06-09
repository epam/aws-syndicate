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
import json

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

