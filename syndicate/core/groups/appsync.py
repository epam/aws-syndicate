import os
from functools import partial

import click

from syndicate.commons.log_helper import get_user_logger
from syndicate.core.constants import APPSYNC_TYPE, APPSYNC_DATA_SOURCE_TYPES, \
    APPSYNC_AUTHENTICATION_TYPES, APPSYNC_AUTHORIZATION_TYPES, \
    APPSYNC_RESOLVER_RUNTIMES, APPSYNC_RESOLVER_KINDS, OK_RETURN_CODE, \
    FAILED_RETURN_CODE
from syndicate.core.decorators import return_code_manager
from syndicate.core.generators.appsync import generate_appsync
from syndicate.core.generators.deployment_resources import \
    BaseConfigurationGenerator
from syndicate.core.generators.deployment_resources.appsync_generator import \
    AppSyncDataSourceGenerator, AppSyncAuthorizationGenerator, \
    AppSyncResolverGenerator, AppSyncFunctionGenerator
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import OrderedGroup, resolve_project_path, \
    DictParamType, check_tags, verbose_option, timeit, OptionRequiredIf, \
    ValidRegionParamType, validate_incompatible_options


USER_LOG = get_user_logger()


@click.group(name=APPSYNC_TYPE, cls=OrderedGroup)
@return_code_manager
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@click.pass_context
def appsync(ctx, project_path):
    """Generates AppSync env and resource meta"""
    if not os.access(project_path, os.F_OK):
        USER_LOG.error(f"The provided path {project_path} doesn't exist")
        return FAILED_RETURN_CODE
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        USER_LOG.error(f"Incorrect permissions for the provided path "
                       f"'{project_path}'")
        return FAILED_RETURN_CODE
    ctx.ensure_object(dict)
    ctx.obj[PROJECT_PATH_PARAM] = project_path
    return OK_RETURN_CODE


@appsync.command(name='api')
@return_code_manager
@click.option('--name', required=True, type=str,
              help="AppSync API name")
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@timeit()
def api(name, project_path, tags):
    """
    Generates required environment for AppSync API
    """
    if not os.access(project_path, os.F_OK):
        USER_LOG.error(f"The provided path {project_path} doesn't exist")
        return FAILED_RETURN_CODE
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        USER_LOG.error(f"Incorrect permissions for the provided path "
                       f"'{project_path}'")
        return FAILED_RETURN_CODE
    generate_appsync(name=name,
                     project_path=project_path,
                     tags=tags)
    return OK_RETURN_CODE


@appsync.command(name='data_source')
@return_code_manager
@click.option('--api_name', required=True, type=str,
              help="AppSync API name to add data source to")
@click.option('--name', required=True, type=str,
              help="Data source name")
@click.option('--description', type=str,
              help="Data source description")
@click.option('--type', type=click.Choice(APPSYNC_DATA_SOURCE_TYPES),
              default='NONE', help="Data source type")
@click.option('--resource_name', type=str, cls=OptionRequiredIf,
              required_if_values=['AWS_LAMBDA', 'AMAZON_DYNAMODB'],
              required_if='type', help="Data source resource name")
@click.option('--region', type=ValidRegionParamType(),
              help="The region where the resource is located. If not "
                   "specified, sets the default value from syndicate config")
@click.option('--service_role_name', type=str, cls=OptionRequiredIf,
              required_if='type',
              required_if_values=['AWS_LAMBDA', 'AMAZON_DYNAMODB'],
              help="The name of the role to access the data source resource")
@verbose_option
@click.pass_context
@timeit()
def data_source(ctx, **kwargs):
    """Adds data source to an existing SyncApp API"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    try:
        generator = AppSyncDataSourceGenerator(**kwargs)
    except ValueError as e:
        raise click.BadParameter(e)
    _generate(generator)
    USER_LOG.info(f"Data source '{kwargs['name']}' was added to AppSync API "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


@appsync.command(name='function')
@return_code_manager
@click.option('--api_name', required=True, type=str,
              help="AppSync API name to add function to")
@click.option('--name', required=True, type=str,
              help="Function name")
@click.option('--description', type=str,
              help="Function description")
@click.option('--data_source_name', required=True, type=str,
              help="The name of the data source to associate the function "
                   "with")
@click.option('--runtime', type=click.Choice(APPSYNC_RESOLVER_RUNTIMES),
              required=True, help="Function runtime")
@verbose_option
@click.pass_context
@timeit()
def function(ctx, **kwargs):
    """Adds function to an existing SyncApp API"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    try:
        generator = AppSyncFunctionGenerator(**kwargs)
    except ValueError as e:
        raise click.BadParameter(e)
    _generate(generator)
    USER_LOG.info(f"The function '{kwargs['name']}' was added to AppSync API "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


@appsync.command(name='resolver')
@return_code_manager
@click.option('--api_name', required=True, type=str,
              help="AppSync API name to add resolver to")
@click.option('--kind', type=click.Choice(APPSYNC_RESOLVER_KINDS),
              required=True, default='UNIT', is_eager=True,
              help="The kind of resolver.")
@click.option('--type_name', required=True, type=str,
              help="The name of the type defined in the API schema")
@click.option('--field_name', required=True, type=str,
              help="The name of the field defined in the API schema to attach "
                   "the resolver to")
@click.option('--data_source_name', type=str, cls=OptionRequiredIf,
              required_if='kind', required_if_values=['UNIT'],
              help="The name of the data source to associate the resolver "
                   "with")
@click.option('--function_name', type=str, multiple=True,
              callback=partial(validate_incompatible_options,
                               incompatible_options=['data_source_name']),
              help="The name of the function to add to the resolver")
@click.option('--runtime', type=click.Choice(APPSYNC_RESOLVER_RUNTIMES),
              required=True, help="Resolver runtime")
@verbose_option
@click.pass_context
@timeit()
def resolver(ctx, **kwargs):
    """Adds resolver to an existing SyncApp API"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    try:
        generator = AppSyncResolverGenerator(**kwargs)
    except ValueError as e:
        raise click.BadParameter(e)
    _generate(generator)
    USER_LOG.info(f"The resolver of the type '{kwargs['type_name']}'  for the "
                  f"field '{kwargs['field_name']}' was added to AppSync API "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


@appsync.command(name='authorization')
@return_code_manager
@click.option('--api_name', required=True, type=str,
              help="AppSync API name to add authorization to")
@click.option('--type', required=True,
              type=click.Choice(APPSYNC_AUTHORIZATION_TYPES),
              help="The authorization type")
@click.option('--auth_type', required=True,
              type=click.Choice(APPSYNC_AUTHENTICATION_TYPES),
              help="The authentication type")
@click.option('--resource_name', type=str, cls=OptionRequiredIf,
              required_if_values=['AWS_LAMBDA', 'AMAZON_COGNITO_USER_POOLS'],
              required_if='auth_type',
              help="Authentication provider resource name")
@click.option('--region', type=ValidRegionParamType(),
              help="The region where the authentication provider resource is "
                   "located. If not specified, sets the default value from "
                   "syndicate config")
@verbose_option
@click.pass_context
@timeit()
def authorization(ctx, **kwargs):
    """Adds authorization to an existing SyncApp API"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    try:
        generator = AppSyncAuthorizationGenerator(**kwargs)
    except ValueError as e:
        raise click.BadParameter(e)
    _generate(generator)
    USER_LOG.info(f"The '{kwargs['type']}' authorization of type "
                  f"'{kwargs['auth_type']}' was added to AppSync API "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


def _generate(generator: BaseConfigurationGenerator):
    """Just some common actions for this module are gathered in here"""
    try:
        generator.write()
    except ValueError as e:
        raise click.BadParameter(e)
    except RuntimeError as e:
        raise click.Abort(e)
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")
