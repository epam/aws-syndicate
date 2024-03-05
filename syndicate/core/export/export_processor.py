import json
import os
import sys

import click

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.constants import OAS_V3_FILE_NAME, API_GATEWAY_TYPE
from syndicate.core.export.configuration_exporter import OASV3Exporter
from syndicate.core.helper import build_path


_LOG = get_logger('syndicate.core.export.export_processor')
USER_LOG = get_user_logger()

EXPORT_PROCESSORS = {
    API_GATEWAY_TYPE: OASV3Exporter
}

RESOURCE_TYPES_MAPPING = {
    API_GATEWAY_TYPE: 'apigateway'
}


def export_specification(deploy_name, bundle_name, output_directory,
                         resource_type, dsl):
    processor_type = EXPORT_PROCESSORS.get(resource_type)
    processor = processor_type()
    resource_key = RESOURCE_TYPES_MAPPING.get(resource_type)
    output = load_deploy_output(bundle_name, deploy_name)
    resource_meta = {key: value for key, value in output.items() if
                     resource_key in key}
    if not resource_meta:
        raise AssertionError(f'Meta for the resource type "{resource_key}" '
                             f'not found in the deploy name "{deploy_name}".')
    _LOG.info(f'Meta for the resource type "{resource_key}" resolved '
              f'successfully')
    output_dir_path = processor.prepare_output_directory(output_directory)
    for arn, meta in resource_meta.items():
        resource_id, specification = processor.export_configuration(arn, meta)
        if not specification:
            continue
        try:
            specification = json.dumps(specification, indent=2)
        except json.JSONDecodeError as e:
            click.echo(f'An error occurred when serialising specification. '
                       f'{e}')
            sys.exit(1)
        _LOG.info(f'Specification for resource "{arn}" exported successfully')
        filename = resource_id + '_' + OAS_V3_FILE_NAME
        output_path = build_path(output_dir_path, filename)
        if os.path.exists(output_path):
            USER_LOG.warn(f'Specification file "{filename}" already exists '
                          f'and will be overwritten.')
        with open(output_path, 'w') as output_file:
            output_file.write(specification)
        _LOG.info(f'Specification saved successfully to the file '
                  f'"{output_path}"')
        click.echo(f'Specification of the "{resource_key}" with ARN "{arn}" '
                   f'saved successfully to the file "{output_path}"')
