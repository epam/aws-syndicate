import json
import os

import click

from syndicate.commons import deep_get
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core import ResourceProvider, CONFIG
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.constants import API_GATEWAY_OPENAPI_TYPE, EXPORT_DIR_NAME, \
    OPENAPI_SPEC_FILE_NAME
from syndicate.core.helper import build_path


_LOG = get_logger('syndicate.core.export.export_processor')
USER_LOG = get_user_logger()


resource = ResourceProvider.instance


class ExportProcessor:

    def resource_processors(self, resource_type):
        return {
            API_GATEWAY_OPENAPI_TYPE: self.export_api_gw_openapi_spec
        }.get(resource_type)

    @staticmethod
    def resource_types_mapping(resource_type):
        return {
            API_GATEWAY_OPENAPI_TYPE: 'apigateway'
        }.get(resource_type)

    @staticmethod
    def export_api_gw_openapi_spec(api_arn, meta):
        api_id = api_arn.split('/')[-1]
        api_stage = deep_get(meta, ['resource_meta', 'deploy_stage'])
        return api_id, resource.api_gw().describe_openapi(api_id=api_id,
                                                          stage_name=api_stage)


def export_specification(deploy_name, bundle_name, output_directory,
                         resource_type):
    resource_key = ExportProcessor().resource_types_mapping(resource_type)
    output = load_deploy_output(bundle_name, deploy_name)
    resource_meta = {key: value for key, value in output.items() if
                     resource_key in key}
    if not resource_meta:
        raise AssertionError(f'Meta for the resource type "{resource_key}" '
                             f'not found in the deploy name "{deploy_name}".')
    _LOG.info(f'Meta for the resource type "{resource_key}" resolved '
              f'successfully')
    if not output_directory:
        output_path = build_path(
            CONFIG.project_path, EXPORT_DIR_NAME)
    elif not os.path.isabs(output_directory):
        output_path = build_path(
            os.getcwd(), output_directory)
    else:
        output_path = output_directory
    os.makedirs(output_path, exist_ok=True)
    processor = ExportProcessor().resource_processors(resource_type)
    for arn, meta in resource_meta.items():
        resource_id, specification = processor(arn, meta)
        try:
            specification = json.dumps(specification, indent=4)
        except json.JSONDecodeError as e:
            click.echo(f'An error occurred when serialising specification. '
                       f'{e}')
        if not specification:
            raise AssertionError(f'Resource not found by the ARN: "{arn}"')
        _LOG.info(f'Specification for resource "{arn}" exported successfully')
        filename = resource_id + '_' + OPENAPI_SPEC_FILE_NAME
        output_path = build_path(output_path, filename)
        if os.path.exists(output_path):
            USER_LOG.warn(f'Specification file "{filename}" already exists '
                          f'and will be overwritten.')
        with open(output_path, 'w') as output_file:
            output_file.write(specification)
        _LOG.info(f'Specification saved successfully to the file '
                  f'"{output_path}"')
        click.echo(f'Specification of the "{resource_key}" with ARN "{arn}" '
                   f'saved successfully to the file "{output_path}"')
