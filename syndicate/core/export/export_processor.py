import json
import os

from syndicate.exceptions import ResourceMetadataError, \
    ResourceProcessingError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.bundle_processor import load_deploy_output
from syndicate.core.constants import OAS_V3_FILE_NAME, API_GATEWAY_TYPE, \
                                    DEFAULT_JSON_INDENT
from syndicate.core.export.configuration_exporter import OASV3Exporter
from syndicate.core.helper import build_path


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

EXPORT_PROCESSORS = {
    API_GATEWAY_TYPE: OASV3Exporter
}

RESOURCE_TYPES_MAPPING = {
    API_GATEWAY_TYPE: 'apigateway'
}


def export_specification(
        *,
        resource_type: str,
        dsl: str,
        deploy_name: str,
        bundle_name: str,
        output_directory: str | None = None,
):
    processor_type = EXPORT_PROCESSORS.get(resource_type)
    processor = processor_type()
    resource_key = RESOURCE_TYPES_MAPPING.get(resource_type)
    output = load_deploy_output(bundle_name, deploy_name)
    resource_meta = \
        {key: value for key, value in output.items() if resource_key in key}
    if not resource_meta:
        raise ResourceMetadataError(
            f'Meta for the resource type "{resource_key}" not found in the '
            f'deploy name "{deploy_name}".'
        )
    _LOG.info(f'Meta for the resource type "{resource_key}" resolved '
              f'successfully')
    output_dir_path = processor.prepare_output_directory(output_directory)
    for arn, meta in resource_meta.items():
        resource_id, specification = processor.export_configuration(arn, meta)
        if not specification:
            continue
        try:
            specification = json.dumps(
                specification, 
                indent=DEFAULT_JSON_INDENT
            )
        except json.JSONDecodeError as e:
            raise ResourceProcessingError(
                f'An error occurred when serialising specification. {e}'
            )
        _LOG.info(f'Specification for resource "{arn}" exported successfully')
        filename = resource_id + '_' + OAS_V3_FILE_NAME
        output_path = build_path(output_dir_path, filename)
        if os.path.exists(output_path):
            USER_LOG.warning(
                f'Specification file "{filename}" already exists and will be '
                f'overwritten.'
            )
        with open(output_path, 'w') as output_file:
            output_file.write(specification)
        _LOG.info(f'Specification saved successfully to the file '
                  f'"{output_path}"')
        USER_LOG.info(
            f'Specification of the "{resource_key}" with ARN "{arn}" '
            f'saved successfully to the file "{output_path}"'
        )
