import click

from syndicate.core.constants import API_GATEWAY_OPENAPI_TYPE
from syndicate.core.export.export_processor import export_specification
from syndicate.core.helper import OrderedGroup, resolve_default_value, timeit, \
    sync_lock
from syndicate.core.project_state.project_state import MODIFICATION_LOCK

EXPORT_GROUP_NAME = 'export'
OPEN_API_RESOURCE_TYPE = 'api_gateway_openapi'


@click.group(name=EXPORT_GROUP_NAME, cls=OrderedGroup)
def export():
    """Exports resources specifications from meta"""


@export.command(name='openapi_spec')
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. This parameter allows the framework '
                   'to decide,which exactly output file should be used. If '
                   'not specified, resolves the latest deploy name')
@click.option('--bundle_name',
              callback=resolve_default_value,
              help='Name of the bundle to export from. '
                   'Default value: name of the latest built bundle')
@click.option('--output_dir',
              help='The directory where an exported specification will be '
                   'saved')
@timeit()
def openapi_spec(deploy_name, bundle_name, output_dir):
    """
    Exports the OpenAPI specification of the API Gateway from the bundle meta
    """
    export_specification(deploy_name=deploy_name,
                         bundle_name=bundle_name,
                         output_directory=output_dir,
                         resource_type=API_GATEWAY_OPENAPI_TYPE)
