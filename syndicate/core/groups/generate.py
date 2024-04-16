"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import os
from functools import partial

import click
from syndicate.core.conf.generator import generate_configuration_files
from syndicate.core.constants import SYNDICATE_WIKI_PAGE, \
    JAVA_LAMBDAS_WIKI_PAGE, SYNDICATE_PROJECT_EXAMPLES_PAGE
from syndicate.core.generators.lambda_function import (
    generate_lambda_function, generate_lambda_layer)
from syndicate.core.generators.project import (generate_project_structure,
                                               PROJECT_PROCESSORS)
from syndicate.core.generators.swagger_ui import generate_swagger_ui
from syndicate.core.groups import RUNTIME_JAVA
from syndicate.core.groups.meta import meta
from syndicate.core.helper import (timeit, OrderedGroup,
                                   check_bundle_bucket_name,
                                   resolve_project_path,
                                   check_lambdas_names, DictParamType,
                                   check_suffix, check_prefix,
                                   check_file_extension,
                                   check_lambda_layer_name,
                                   check_lambda_existence, verbose_option)

GENERATE_GROUP_NAME = 'generate'
GENERATE_PROJECT_COMMAND_NAME = 'project'
GENERATE_CONFIG_COMMAND_NAME = 'config'
PROJECT_PATH_HELP = 'Path to project folder. ' \
                    'Default value: current working directory'


@click.group(name=GENERATE_GROUP_NAME, cls=OrderedGroup)
def generate():
    """Generates project, lambda or configs"""


@generate.command(name=GENERATE_PROJECT_COMMAND_NAME)
@click.option('--name', nargs=1, required=True, help='The project name')
@click.option('--path', nargs=1,
              help=PROJECT_PATH_HELP)
@verbose_option
@timeit()
def project(name, path):
    """
    Generates project with all the necessary components and in a right
    folders/files hierarchy to start developing in a min.
    """
    click.echo(f'Project name: {name}')

    proj_path = os.getcwd() if not path else path
    if not os.access(proj_path, os.X_OK | os.W_OK):
        click.echo(
            f"Incorrect permissions for the provided path '{proj_path}'")
        return
    click.echo(f'Project path: {proj_path}')
    generate_project_structure(project_name=name,
                               project_path=proj_path)


@generate.command(name='lambda')
@click.option('--name', multiple=True, type=str,
              required=True, callback=check_lambdas_names,
              help='(multiple) The lambda function name')
@click.option('--runtime', required=True,
              help='Lambda\'s runtime. If multiple lambda names are specified,'
                   ' the runtime will be applied to all lambdas',
              type=click.Choice(PROJECT_PROCESSORS))
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@verbose_option
@timeit()
def lambda_function(name, runtime, project_path):
    """
    Generates required environment for lambda function
    """
    if not os.access(project_path, os.F_OK):
        click.echo(f"The provided path {project_path} doesn't exist")
        return
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        click.echo(f"Incorrect permissions for the provided path "
                   f"'{project_path}'")
        return
    click.echo(f'Lambda names: {name}')
    click.echo(f'Runtime: {runtime}')
    click.echo(f'Project path: {project_path}')
    generate_lambda_function(project_path=project_path,
                             runtime=runtime,
                             lambda_names=name)


@generate.command(name='lambda_layer')
@click.option('--name', type=str, required=True,
              callback=check_lambda_layer_name,
              help='The lambda layer name')
@click.option('--runtime', required=True,
              type=click.Choice(PROJECT_PROCESSORS),
              help='Lambda layer\'s runtime.')
@click.option('--link_with_lambda', required=False,
              type=str, multiple=True, callback=check_lambda_existence,
              help='(multiple) Lambda function name to link the layer with.')
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@verbose_option
@timeit()
def lambda_layer(name, runtime, link_with_lambda, project_path):
    """
    Generates required environment for lambda function's layer
    """
    if runtime == RUNTIME_JAVA:
        click.echo('Generation of lambda layer for Java runtime is currently '
                   'unsupported. \nA layer for lambda with Java runtime can '
                   'be added to the project by using the annotation '
                   '\'@LambdaLayer\'. \nMore details can be found on the '
                   'aws-syndicate wiki page or in the project examples:\n'
                   f'{SYNDICATE_WIKI_PAGE + JAVA_LAMBDAS_WIKI_PAGE}'
                   f'\n{SYNDICATE_PROJECT_EXAMPLES_PAGE + runtime}')
        return
    if not os.access(project_path, os.F_OK):
        click.echo(f"The provided path {project_path} doesn't exist")
        return
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        click.echo(f"Incorrect permissions for the provided path "
                   f"'{project_path}'")
        return
    click.echo(f'Project path: {project_path}')
    generate_lambda_layer(name=name,
                          runtime=runtime,
                          lambda_names=link_with_lambda,
                          project_path=project_path)


@generate.command(name=GENERATE_CONFIG_COMMAND_NAME)
@click.option('--name',
              required=True,
              help='Name of the configuration to create. '
                   'Generated config will be created in folder '
                   '.syndicate-config-{name}. May contain name '
                   'of the environment')
@click.option('--region',
              help='The region that is used to deploy the application',
              required=True)
@click.option('--bundle_bucket_name',
              help='Name of the bucket that is used for uploading artifacts.'
                   ' It will be created if specified.', required=True,
              callback=check_bundle_bucket_name)
@click.option('--access_key',
              help='AWS access key id that is used to deploy the application. '
                   'Retrieved from session by default')
@click.option('--secret_key',
              help='AWS secret key that is used to deploy the application. '
                   'Retrieved from session by default')
@click.option('--session_token',
              help='AWS session token that is used to deploy the application. '
                   'Retrieved from session by default')
@click.option('--config_path',
              help='Path to store generated configuration file')
@click.option('--project_path',
              help=PROJECT_PATH_HELP)
@click.option('--prefix',
              help='Prefix that is added to project names while deployment '
                   'by pattern: {prefix}resource_name{suffix}. '
                   'Must be less than or equal to 5. If --extended_prefix '
                   'specified prefix length may be up to 14 symbols',
              callback=check_prefix)
@click.option('--suffix',
              help='Suffix that is added to project names while deployment '
                   'by pattern: {prefix}resource_name{suffix}. '
                   'Must be less than or equal to 5',
              callback=check_suffix)
@click.option('--extended_prefix', type=bool, default=False,
              is_eager=True,
              help='Extends the length of the prefix up to 14 symbols. '
                   'If specified, a prefix and a suffix will be added to all '
                   'project resources.')
@click.option('--use_temp_creds', type=bool, default=False,
              help='Indicates Syndicate to generate and use temporary AWS '
                   'credentials')
@click.option('--access_role', type=str,
              help='Indicates Syndicate to use this role\'s temporary AWS '
                   'credentials. Cannot be used if \'--use_temp_creds\' is '
                   'equal to true')
@click.option('--serial_number', type=str,
              help='The identification number of the MFA device that is '
                   'associated with the IAM user which will be used for '
                   'deployment. If specified MFA token will be asked before '
                   'making actions')
@click.option('--tags', type=DictParamType(),
              help='Tags to add to the config. They will be added to all the '
                   'resources during deployment')
@click.option('--iam_permissions_boundary', type=str,
              help='Common permissions boundary arn to add to all the roles')
@click.option('--lock_lifetime_minutes', type=click.IntRange(min=0, max=300),
              help='Project lock lifetime in minutes (see section "locks" '
                   'in ".syndicate"). The default value is 20 minutes.')
@verbose_option
@timeit()
def config(name, config_path, project_path, region, access_key, secret_key,
           session_token, bundle_bucket_name, prefix, suffix,
           extended_prefix, use_temp_creds, access_role, serial_number,
           tags, iam_permissions_boundary, lock_lifetime_minutes):
    """
    Creates Syndicate configuration files
    """
    generate_configuration_files(name=name,
                                 config_path=config_path,
                                 project_path=project_path,
                                 region=region,
                                 access_key=access_key,
                                 secret_key=secret_key,
                                 session_token=session_token,
                                 bundle_bucket_name=bundle_bucket_name,
                                 prefix=prefix,
                                 suffix=suffix,
                                 extended_prefix=extended_prefix,
                                 use_temp_creds=use_temp_creds,
                                 access_role=access_role,
                                 serial_number=serial_number,
                                 tags=tags,
                                 iam_permissions_boundary=iam_permissions_boundary,
                                 lock_lifetime_minutes=lock_lifetime_minutes)


@generate.command(name='swagger_ui')
@click.option('--name', required=True, type=str,
              help="Swagger UI name")
@click.option('--path_to_spec', required=True, type=str,
              callback=partial(check_file_extension, extensions=['.json']),
              help="Path to OpenAPI specification file. Path that is relative "
                   "to the project path can be specified.")
@click.option('--target_bucket', required=True, type=str,
              callback=check_bundle_bucket_name,
              help="S3 bucket name for Swagger UI deployment")
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@verbose_option
@timeit()
def swagger_ui(name, path_to_spec, target_bucket, project_path):
    """
    Generates required environment for Swagger UI
    """
    if not os.access(project_path, os.F_OK):
        click.echo(f"The provided path {project_path} doesn't exist")
        return
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        click.echo(f"Incorrect permissions for the provided path "
                   f"'{project_path}'")
        return
    generate_swagger_ui(name=name,
                        spec_path=path_to_spec,
                        target_bucket=target_bucket,
                        project_path=project_path)


generate.add_command(meta)
