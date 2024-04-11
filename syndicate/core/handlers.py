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
import json
import os
import sys

import click
from tabulate import tabulate

from syndicate.core.export.export_processor import export_specification
from syndicate.core.transform.transform_processor import generate_build_meta
from syndicate.core import initialize_connection, \
    initialize_project_state, initialize_signal_handling
from syndicate.core.build.artifact_processor import (RUNTIME_NODEJS,
                                                     assemble_artifacts,
                                                     RUNTIME_JAVA,
                                                     RUNTIME_PYTHON,
                                                     RUNTIME_SWAGGER_UI)
from syndicate.core.build.bundle_processor import (create_bundles_bucket,
                                                   load_bundle,
                                                   upload_bundle_to_s3,
                                                   if_bundle_exist)
from syndicate.core.build.deployment_processor import (
    continue_deployment_resources, create_deployment_resources,
    remove_deployment_resources, remove_failed_deploy_resources,
    update_deployment_resources)
from syndicate.core.build.meta_processor import create_meta
from syndicate.core.build.profiler_processor import (get_metric_statistics,
                                                     process_metrics)
from syndicate.core.build.warmup_processor import (process_deploy_resources,
                                                   process_api_gw_resources,
                                                   warm_upper,
                                                   process_existing_api_gw_id,
                                                   process_inputted_api_gw_id)
from syndicate.core.conf.validator import (JAVA_LANGUAGE_NAME,
                                           PYTHON_LANGUAGE_NAME,
                                           NODEJS_LANGUAGE_NAME,
                                           SWAGGER_UI_NAME)
from syndicate.core.decorators import (check_deploy_name_for_duplicates,
                                       check_deploy_bucket_exists)
from syndicate.core.groups.generate import (generate,
                                            GENERATE_PROJECT_COMMAND_NAME,
                                            GENERATE_CONFIG_COMMAND_NAME)
from syndicate.core.groups.tags import tags
from syndicate.core.helper import (create_bundle_callback,
                                   handle_futures_progress_bar,
                                   resolve_path_callback, timeit,
                                   verify_bundle_callback, sync_lock,
                                   resolve_default_value, ValidRegionParamType,
                                   generate_default_bundle_name,
                                   resolve_and_verify_bundle_callback,
                                   param_to_lower, verbose_option)
from syndicate.core.project_state.project_state import (MODIFICATION_LOCK,
                                                        WARMUP_LOCK)
from syndicate.core.project_state.status_processor import project_state_status
from syndicate.core.project_state.sync_processor import sync_project_state
from syndicate.core.constants import TEST_ACTION, BUILD_ACTION, \
    DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION, SYNC_ACTION, \
    STATUS_ACTION, WARMUP_ACTION, PROFILER_ACTION, ASSEMBLE_JAVA_MVN_ACTION, \
    ASSEMBLE_PYTHON_ACTION, ASSEMBLE_NODE_ACTION, ASSEMBLE_ACTION, \
    PACKAGE_META_ACTION, CREATE_DEPLOY_TARGET_BUCKET_ACTION, UPLOAD_ACTION, \
    COPY_BUNDLE_ACTION, EXPORT_ACTION, ASSEMBLE_SWAGGER_UI_ACTION

INIT_COMMAND_NAME = 'init'
SYNDICATE_PACKAGE_NAME = 'aws-syndicate'
HELP_PARAMETER_KEY = '--help'
commands_without_config = (
    INIT_COMMAND_NAME,
    GENERATE_PROJECT_COMMAND_NAME,
    GENERATE_CONFIG_COMMAND_NAME,
    HELP_PARAMETER_KEY
)


def _not_require_config(all_params):
    return any(item in commands_without_config for item in all_params)


@click.group(name='syndicate')
@click.version_option()
def syndicate():
    from syndicate.core import CONF_PATH
    if _not_require_config(sys.argv):
        pass
    elif CONF_PATH:
        click.echo('Configuration used: ' + CONF_PATH)
        initialize_connection()
        initialize_project_state()
        initialize_signal_handling()
    else:
        click.echo('Environment variable SDCT_CONF is not set! '
                   'Please verify that you have provided path to '
                   'correct config files '
                   'or execute `syndicate generate config` command.')
        sys.exit(1)


@syndicate.command(name=TEST_ACTION)
@click.option('--suite', default='unittest',
              type=click.Choice(['unittest', 'pytest', 'nose'],
                                case_sensitive=False),
              help='Supported testing frameworks. Possible options: unittest, '
                   'pytest, nose. Default value: unittest')
@click.option('--test_folder_name', nargs=1, default='tests',
              help='Directory in the project that contains tests to run. '
                   'Default folder: tests')
@click.option('--errors_allowed', is_flag=True,
              help='Flag to return successful response even if some tests '
                   'fail')
@verbose_option
@timeit(action_name=TEST_ACTION)
def test(suite, test_folder_name, errors_allowed):
    """Discovers and runs tests inside python project configuration path."""
    click.echo('Running tests...')
    import subprocess
    from syndicate.core import CONFIG
    project_path = CONFIG.project_path
    test_folder = os.path.join(project_path, test_folder_name)
    if not os.path.exists(test_folder):
        click.echo(f'Tests not found, \'{test_folder_name}\' folder is missing'
                   f' in \'{project_path}\'.')
        return
    test_lib_command_mapping = {
        'unittest': f'{sys.executable} -m unittest discover {test_folder} -v',
        'pytest': 'pytest --no-header -v',
        'nose': 'nosetests --verbose'
    }

    command = test_lib_command_mapping.get(suite)
    result = subprocess.run(command.split(), cwd=project_path)

    if not errors_allowed:
        if result.returncode != 0:
            click.echo('Some tests failed. Exiting.')
            sys.exit(1)
    click.echo('Tests passed.')


@syndicate.command(name=BUILD_ACTION)
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle to build. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%SZ')
@click.option('--force_upload', '-F', is_flag=True, default=False,
              help='Flag to override existing bundle with the same name')
@click.option('--errors_allowed', is_flag=True, default=False,
              help='Flag to continue bundle building if some tests fail')
@verbose_option
@click.pass_context
@check_deploy_bucket_exists
@timeit(action_name=BUILD_ACTION)
def build(ctx, bundle_name, force_upload, errors_allowed):
    """
    Builds bundle of an application
    """
    if if_bundle_exist(bundle_name=bundle_name) and not force_upload:
        click.echo(f'Bundle name \'{bundle_name}\' already exists '
                   f'in deploy bucket. Please use another bundle '
                   f'name or delete the bundle')
        return
    ctx.invoke(test, errors_allowed=errors_allowed)
    ctx.invoke(assemble, bundle_name=bundle_name)
    ctx.invoke(package_meta, bundle_name=bundle_name)
    ctx.invoke(upload, bundle_name=bundle_name, force_upload=force_upload)


@syndicate.command(name='transform')
@click.option('--bundle_name',
              callback=resolve_default_value,
              help='Name of the bundle to transform. '
                   'Default value: name of the latest built bundle')
@click.option('--dsl', type=click.Choice(['CloudFormation', 'Terraform'],
                                         case_sensitive=False),
              callback=param_to_lower,
              multiple=True, required=True,
              help='Type of the IaC provider')
@click.option('--output_dir',
              help='The directory where a transformed template will be saved')
@verbose_option
@timeit()
def transform(bundle_name, dsl, output_dir):
    """
    Transforms the meta-description of a bundle to a template
    compatible with the specified IaC provider
    """
    generate_build_meta(bundle_name=bundle_name,
                        dsl_list=dsl,
                        output_directory=output_dir)


@syndicate.command(name=DEPLOY_ACTION)
@sync_lock(lock_type=MODIFICATION_LOCK)
@click.option('--deploy_name', '-d', callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--bundle_name', '-b', callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_only_types', '-types', multiple=True,
              help='Types of the resources to deploy')
@click.option('--deploy_only_resources', '-resources', multiple=True,
              help='Names of the resources to deploy')
@click.option('--deploy_only_resources_path', '-path', nargs=1,
              help='Path to file containing names of the resources to deploy')
@click.option('--excluded_resources', '-exresources', multiple=True,
              help='Names of the resources to skip while deploy.')
@click.option('--excluded_resources_path', '-expath', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--excluded_types', '-extypes', multiple=True,
              help='Types of the resources to skip while deploy')
@click.option('--continue_deploy', is_flag=True,
              help='Flag to continue failed deploy')
@click.option('--replace_output', is_flag=True, default=False,
              help='Flag to replace the existing deploy output')
@verbose_option
@check_deploy_name_for_duplicates
@check_deploy_bucket_exists
@timeit(action_name=DEPLOY_ACTION)
def deploy(deploy_name, bundle_name, deploy_only_types, deploy_only_resources,
           deploy_only_resources_path, excluded_resources,
           excluded_resources_path, excluded_types, continue_deploy,
           replace_output):
    """
    Deploys the application infrastructure
    """
    if deploy_only_resources_path and os.path.exists(
            deploy_only_resources_path):
        deploy_resources_list = json.load(open(deploy_only_resources_path))
        deploy_only_resources = tuple(
            set(deploy_only_resources + tuple(deploy_resources_list)))
    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))
    if continue_deploy:
        deploy_success = continue_deployment_resources(deploy_name,
                                                       bundle_name,
                                                       deploy_only_resources,
                                                       deploy_only_types,
                                                       excluded_resources,
                                                       excluded_types,
                                                       replace_output)

    else:
        deploy_success = create_deployment_resources(deploy_name, bundle_name,
                                                     deploy_only_resources,
                                                     deploy_only_types,
                                                     excluded_resources,
                                                     excluded_types,
                                                     replace_output)
    click.echo('Backend resources were deployed{0}.'.format(
        '' if deploy_success else ' with errors. See deploy output file'))


@syndicate.command(name=UPDATE_ACTION)
@sync_lock(lock_type=MODIFICATION_LOCK)
@click.option('--bundle_name', '-b', callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_name', '-d', callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--update_only_types', '-types', multiple=True,
              help='Types of the resources to update')
@click.option('--update_only_resources', '-resources', multiple=True,
              help='Names of the resources to deploy')
@click.option('--update_only_resources_path', '-path', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--replace_output', nargs=1, is_flag=True, default=False,
              help='The flag to replace the existing deploy output file')
@verbose_option
@check_deploy_name_for_duplicates
@check_deploy_bucket_exists
@timeit(action_name=UPDATE_ACTION)
def update(bundle_name, deploy_name, replace_output,
           update_only_resources,
           update_only_resources_path,
           update_only_types=[]):
    """
    Updates infrastructure from the provided bundle
    """
    click.echo('Bundle name: {}'.format(bundle_name))
    if update_only_types:
        click.echo('Types to update: {}'.format(list(update_only_types)))
    if update_only_resources:
        click.echo(
            'Resources to update: {}'.format(list(update_only_resources)))
    if update_only_resources_path:
        click.echo('Path to list of resources to update: {}'.format(
            update_only_resources_path))

    if update_only_resources_path and os.path.exists(
            update_only_resources_path):
        update_resources_list = json.load(open(update_only_resources_path))
        update_only_resources = tuple(
            set(update_only_resources + tuple(update_resources_list)))
    success = update_deployment_resources(
        bundle_name=bundle_name,
        deploy_name=deploy_name,
        update_only_types=update_only_types,
        update_only_resources=update_only_resources,
        replace_output=replace_output)
    if success:
        click.echo('Update of resources has been successfully completed')
    else:
        click.echo('Something went wrong during resources update')


@syndicate.command(name=CLEAN_ACTION)
@sync_lock(lock_type=MODIFICATION_LOCK)
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. This parameter allows the framework '
                   'to decide,which exactly output file should be used. The '
                   'resources are cleaned based on the output file which is '
                   'created during the deployment process. If not specified, '
                   'resolves the latest deploy name')
@click.option('--bundle_name', '-b', nargs=1, callback=resolve_default_value,
              help='Name of the bundle. If not specified, resolves the latest '
                   'bundle name')
@click.option('--clean_only_types', '-types', multiple=True,
              help='If specified only provided types will be cleaned')
@click.option('--clean_only_resources', '-resources', multiple=True,
              help='If specified only provided resources will be cleaned')
@click.option('--clean_only_resources_path', '-path', nargs=1, type=str,
              help='If specified only resources path will be cleaned')
@click.option('--clean_externals', nargs=1, is_flag=True, default=False,
              help='Flag. If specified only external resources will be '
                   'cleaned')
@click.option('--excluded_resources', '-exresources', multiple=True,
              help='If specified provided resources will be excluded')
@click.option('--excluded_resources_path', '-expath', nargs=1, type=str,
              help='If specified provided resource path will be excluded')
@click.option('--excluded_types', '-extypes', multiple=True,
              help='If specified provided types will be excluded')
@click.option('--rollback', is_flag=True,
              help='Remove failed deployed resources')
@click.option('--preserve_state', is_flag=True,
              help='Preserve deploy output json file after resources removal')
@verbose_option
@timeit(action_name=CLEAN_ACTION)
def clean(deploy_name, bundle_name, clean_only_types, clean_only_resources,
          clean_only_resources_path, clean_externals, excluded_resources,
          excluded_resources_path, excluded_types, rollback, preserve_state):
    """
    Cleans the application infrastructure
    """
    click.echo('Command clean')
    click.echo(f'Deploy name: {deploy_name}')
    separator = ', '
    if clean_only_types:
        click.echo(f'Clean only types: {separator.join(clean_only_types)}')
    if clean_only_resources:
        click.echo(f'Clean only resources: '
                   f'{separator.join(clean_only_resources)}')
    if clean_only_resources_path:
        click.echo(f'Clean only resources path: {clean_only_resources_path}')
    if excluded_resources:
        click.echo(f'Excluded resources: {separator.join(excluded_resources)}')
    if excluded_resources_path:
        click.echo(f'Excluded resources path: {excluded_resources_path}')
    if excluded_types:
        click.echo(f'Excluded types: {separator.join(excluded_resources)}')
    if clean_only_resources_path and os.path.exists(clean_only_resources_path):
        clean_resources_list = json.load(open(clean_only_resources_path))
        clean_only_resources = tuple(
            set(clean_only_resources + tuple(clean_resources_list)))
    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))
    if rollback:
        result = remove_failed_deploy_resources(
            deploy_name=deploy_name, bundle_name=bundle_name,
            clean_only_resources=clean_only_resources,
            clean_only_types=clean_only_types,
            excluded_resources=excluded_resources,
            excluded_types=excluded_types, clean_externals=clean_externals,
            preserve_state=preserve_state
        )
    else:
        result = remove_deployment_resources(
            deploy_name=deploy_name,
            bundle_name=bundle_name,
            clean_only_resources=clean_only_resources,
            clean_only_types=clean_only_types,
            excluded_resources=excluded_resources,
            excluded_types=excluded_types,
            clean_externals=clean_externals,
            preserve_state=preserve_state)
    click.echo('AWS resources were removed.')
    return result


@syndicate.command(name=SYNC_ACTION)
@verbose_option
@check_deploy_bucket_exists
@timeit()
def sync():
    """
    Syncs the state of local project state file (.syndicate) and
    the remote one.
    """
    return sync_project_state()


@syndicate.command(name=STATUS_ACTION)
@click.option('--events', 'category', flag_value='events',
              help='Show event logs of the project')
@click.option('--resources', 'category', flag_value='resources',
              help='Show a summary of the project resources')
@verbose_option
@check_deploy_bucket_exists
@timeit()
def status(category):
    """
    Shows the state of a local project state file (.syndicate).
    Command displays the following content: project name, state, latest
    modification, locks summary, latest event, project resources.

    NOTE: The flags are incompatible and the status is displayed according to
    the first entered flag.
    """
    click.echo(project_state_status(category))


@syndicate.command(name=WARMUP_ACTION)
@sync_lock(lock_type=WARMUP_LOCK)
@click.option('--bundle_name', '-b', nargs=1, callback=resolve_default_value,
              help='Name of the bundle. If not specified, resolves the latest '
                   'bundle name')
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. If not specified, resolves the latest '
                   'deploy name')
@click.option('--api_gw_id', '-api', nargs=1, multiple=True, type=str,
              help='Provide API Gateway IDs to warmup')
@click.option('--stage_name', '-stage', nargs=1, multiple=True, type=str,
              help='Name of stages of provided API Gateway IDs')
@click.option('--lambda_auth', '-auth', default=False, is_flag=True,
              help='Flag. Should be specified if API Gateway Lambda Authorizer'
                   ' is enabled')
@click.option('--header_name', '-hname', nargs=1,
              help='Name of authentication header.')
@click.option('--header_value', '-hvalue',
              nargs=1, help='Authentication header value.')
@verbose_option
@check_deploy_bucket_exists
@timeit(action_name=WARMUP_ACTION)
def warmup(bundle_name, deploy_name, api_gw_id, stage_name, lambda_auth,
           header_name, header_value):
    """
    Warmups Lambda functions
    """

    if bundle_name and deploy_name:
        click.echo(f'Deploy name: {deploy_name}')
        if not if_bundle_exist(bundle_name=bundle_name):
            click.echo(f'Bundle name \'{bundle_name}\' does not exists '
                       'in deploy bucket. Please use another bundle '
                       'name or create the bundle')
            return

        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_deploy_resources(deploy_name=deploy_name,
                                     bundle_name=bundle_name)

    elif api_gw_id:
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_inputted_api_gw_id(api_id=api_gw_id, stage_name=stage_name,
                                       echo=click.echo)

    else:
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_existing_api_gw_id(stage_name=stage_name, echo=click.echo)

    if not paths_to_be_triggered or not resource_path_warmup_key_mapping:
        click.echo('No resources to warm up')
        return
    resource_method_mapping, resource_warmup_key_mapping = \
        process_api_gw_resources(paths_to_be_triggered=paths_to_be_triggered,
                                 resource_path_warmup_key_mapping=
                                 resource_path_warmup_key_mapping)
    warm_upper(resource_method_mapping=resource_method_mapping,
               resource_warmup_key_mapping=resource_warmup_key_mapping,
               lambda_auth=lambda_auth, header_name=header_name,
               header_value=header_value)
    click.echo('Application resources have been warmed up.')


@syndicate.command(name=PROFILER_ACTION)
@click.option('--bundle_name', '-b', nargs=1, callback=resolve_default_value,
              help='The name of the bundle from which to select lambdas for '
                   'collecting metrics. If not specified, resolves the latest '
                   'bundle name')
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. If not specified, resolves the latest '
                   'deploy name')
@click.option('--from_date', '-from', nargs=1,
              type=click.DateTime(formats=['%Y-%m-%dT%H:%M:%SZ']),
              help='Date from which collect lambda metrics. The '
                   '\'--to_date\' parameter required. Example of the date '
                   'format: 2022-02-02T02:02:02Z')
@click.option('--to_date', '-to', nargs=1,
              type=click.DateTime(formats=['%Y-%m-%dT%H:%M:%SZ']),
              help='Date until which collect lambda metrics. The '
                   '\'--from_date\' parameter required. Example of the date '
                   'format: 2022-02-02T02:02:02Z')
@verbose_option
@check_deploy_bucket_exists
def profiler(bundle_name, deploy_name, from_date, to_date):
    """
    Displays application Lambda metrics
    """
    metric_value_dict = get_metric_statistics(bundle_name, deploy_name,
                                              from_date, to_date)
    for lambda_name, metrics in metric_value_dict.items():
        prettify_metrics_dict = {}

        click.echo(f'{os.linesep}Lambda function name: {lambda_name}')
        prettify_metrics_dict = process_metrics(prettify_metrics_dict, metrics)
        if not prettify_metrics_dict:
            click.echo('No executions found')
        click.echo(tabulate(prettify_metrics_dict, headers='keys',
                            stralign='right'))


# =============================================================================


@syndicate.command(name=ASSEMBLE_JAVA_MVN_ACTION)
@timeit()
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle, to which the build artifacts are '
                   'gathered and later used for the deployment. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback, required=True,
              help='The path to the Java project. The provided path is the '
                   'path for an mvn clean install. The artifacts are copied '
                   'to a folder, which is be later used as the deployment '
                   'bundle (the bundle path: bundles/${bundle_name})')
@verbose_option
@timeit(action_name=ASSEMBLE_JAVA_MVN_ACTION)
def assemble_java_mvn(bundle_name, project_path):
    """
    Builds Java lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo(f'Command compile java project path: {project_path}')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_JAVA)
    click.echo('Java artifacts were prepared successfully.')


@syndicate.command(name=ASSEMBLE_PYTHON_ACTION)
@timeit()
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle, to which the build artifacts are '
                   'gathered and later used for the deployment. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback, required=True,
              help='The path to the Python project. The code is '
                   'packed to a zip archive, where the external libraries are '
                   'found, which are described in the requirements.txt file, '
                   'and internal project dependencies according to the '
                   'described in local_requirements.txt file')
@verbose_option
@timeit(action_name=ASSEMBLE_PYTHON_ACTION)
def assemble_python(bundle_name, project_path):
    """
    Builds Python lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo(f'Command assemble python: project_path: {project_path} ')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_PYTHON)
    click.echo('Python artifacts were prepared successfully.')


@syndicate.command(name=ASSEMBLE_NODE_ACTION)
@timeit()
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle, to which the build artifacts are '
                   'gathered and later used for the deployment. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback, required=True,
              help='The path to the NodeJS project. The code is '
                   'packed to a zip archive, where the external libraries are '
                   'found, which are described in the package.json file')
@verbose_option
@timeit(action_name=ASSEMBLE_NODE_ACTION)
def assemble_node(bundle_name, project_path):
    """
    Builds NodeJS lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo(f'Command assemble node: project_path: {project_path} ')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_NODEJS)
    click.echo('NodeJS artifacts were prepared successfully.')


@syndicate.command(name=ASSEMBLE_SWAGGER_UI_ACTION)
@timeit()
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle, to which the build artifacts are '
                   'gathered and later used for the deployment. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback, required=True,
              help='The path to the project. Related files will be packed '
                   'into a zip archive.')
@verbose_option
@timeit(action_name=ASSEMBLE_SWAGGER_UI_ACTION)
def assemble_swagger_ui(bundle_name, project_path):
    """
        Builds Swagger UI artifacts

        \f
        :param bundle_name: name of the bundle
        :param project_path: path to project folder
        :return:
        """
    click.echo(f'Command assemble Swagger UI: project_path: {project_path} ')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_SWAGGER_UI)
    click.echo('Swagger UI artifacts were prepared successfully.')


RUNTIME_LANG_TO_BUILD_MAPPING = {
    JAVA_LANGUAGE_NAME: assemble_java_mvn,
    PYTHON_LANGUAGE_NAME: assemble_python,
    NODEJS_LANGUAGE_NAME: assemble_node,
    SWAGGER_UI_NAME: assemble_swagger_ui
}


@syndicate.command(name=ASSEMBLE_ACTION)
@click.option('--bundle_name', '-b', callback=generate_default_bundle_name,
              help='Bundle\'s name to build the lambdas in. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@verbose_option
@click.pass_context
@timeit(action_name=ASSEMBLE_ACTION)
def assemble(ctx, bundle_name):
    """
    Builds the application artifacts

    \f
    :param ctx:
    :param bundle_name: name of the bundle to which the artifacts
        will be associated
    :return:
    """
    click.echo(f'Building artifacts, bundle: {bundle_name}')
    from syndicate.core import PROJECT_STATE
    # Updates stale lambda state aggregation
    PROJECT_STATE.refresh_lambda_state()

    build_mapping_dict: dict = PROJECT_STATE.load_project_build_mapping()
    if build_mapping_dict:
        for key, value in build_mapping_dict.items():
            func = RUNTIME_LANG_TO_BUILD_MAPPING.get(key)
            if func:
                ctx.invoke(func, bundle_name=bundle_name,
                           project_path=value)
            else:
                click.echo(f'Build tool is not supported: {key}')
    else:
        click.echo('Projects to be built are not found')


@syndicate.command(name=PACKAGE_META_ACTION)
@click.option('--bundle_name', '-b', required=True,
              callback=verify_bundle_callback,
              help='Bundle\'s name to package the current meta in')
@verbose_option
@timeit(action_name=PACKAGE_META_ACTION)
def package_meta(bundle_name):
    """
    Generates metadata about the application infrastructure

    \f
    :param bundle_name: name of the bundle to generate metadata
    :return:
    """
    from syndicate.core import CONFIG
    click.echo(f'Package meta, bundle: {bundle_name}')
    create_meta(project_path=CONFIG.project_path,
                bundle_name=bundle_name)
    click.echo('Meta was configured successfully.')


@syndicate.command(name=CREATE_DEPLOY_TARGET_BUCKET_ACTION)
@verbose_option
@timeit()
def create_deploy_target_bucket():
    """
    Creates a bucket in AWS account where all bundles will be uploaded
    """
    from syndicate.core import CONFIG
    click.echo(f'Create deploy target sdk: {CONFIG.deploy_target_bucket}')
    create_bundles_bucket()
    click.echo('Deploy target bucket was created successfully')


@syndicate.command(name=UPLOAD_ACTION)
@click.option('--bundle_name', '-b',
              callback=resolve_and_verify_bundle_callback,
              help='Bundle name to which the build artifacts are gathered '
                   'and later used for the deployment. NOTE: if not '
                   'specified, the latest build will be uploaded')
@click.option('--force_upload', '-F', is_flag=True,
              help='Flag to override existing bundle with the same name as '
                   'provided')
@verbose_option
@check_deploy_bucket_exists
@timeit(action_name=UPLOAD_ACTION)
def upload(bundle_name, force_upload=False):
    """
    Uploads bundle from local storage to AWS S3

    \f
    :param bundle_name: name of the bundle to upload
    :param force_upload: used if the bundle with the same name as provided
        already exists in an account
    :return:
    """
    click.echo(f'Upload bundle: {bundle_name}')
    if force_upload:
        click.echo('Force upload')

    futures = upload_bundle_to_s3(bundle_name=bundle_name, force=force_upload)
    handle_futures_progress_bar(futures)

    click.echo('Bundle was uploaded successfully')


@syndicate.command(name=COPY_BUNDLE_ACTION)
@click.option('--bundle_name', '-b', nargs=1, callback=create_bundle_callback,
              required=True,
              help='The bundle name, to which the build artifacts '
                   'are gathered and later used for the deployment')
@click.option('--src_account_id', '-acc_id', nargs=1, required=True,
              help='The account ID, to which the bundle is to be '
                   'uploaded')
@click.option('--src_bucket_region', '-r', nargs=1, required=True,
              type=ValidRegionParamType(),
              help='The name of the region of the bucket where target bundle '
                   'is stored')
@click.option('--src_bucket_name', '-bucket', nargs=1, required=True,
              help='The name of the bucket where target bundle is stored')
@click.option('--role_name', '-role', nargs=1, required=True,
              help='The role name from the specified account, which is '
                   'assumed. Here you have to check the trusted relationship '
                   'between the accounts. The active account must be a trusted'
                   ' one for the account which is specified in the command')
@click.option('--force_upload', '-F', is_flag=True, default=False,
              help='Flag. Used if the bundle with the same name as provided '
                   'already exists in a target account')
@verbose_option
@timeit()
@click.pass_context
def copy_bundle(ctx, bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name, force_upload):
    """
    Copies the bundle from the specified account-region-bucket to
    account-region-bucket specified in syndicate.yml

    \f
    :param ctx:
    :param bundle_name: name of the bundle to copy
    :param src_account_id: id of the account where target bundle is stored
    :param src_bucket_region: region of the bucket where target bundle
        is stored
    :param src_bucket_name: name of the bucket where target bundle is stored
    :param role_name: name of the role that is assumed while copying
    :param force_upload: used if the bundle with the same name as provided
        already exists in a target account
    :return:
    """
    click.echo(f'Copy bundle: {bundle_name}')
    click.echo(f'Bundle name: {bundle_name}')
    click.echo(f'Source account id: {src_account_id}')
    click.echo(f'Source bucket region: {src_bucket_region}')
    click.echo(f'Source bucket name: {src_bucket_name}')
    futures = load_bundle(bundle_name, src_account_id, src_bucket_region,
                          src_bucket_name, role_name)
    handle_futures_progress_bar(futures)
    click.echo('Bundle was downloaded successfully')
    ctx.invoke(upload, bundle_name=bundle_name, force=force_upload)
    click.echo('Bundle was copied successfully')


@syndicate.command(name=EXPORT_ACTION)
@click.option('--resource_type',
              type=click.Choice(['api_gateway']), required=True,
              help='The type of resource to export configuration')
@click.option('--dsl',
              type=click.Choice(['oas_v3']), default='oas_v3',
              help='DSL of output specification')
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. This parameter allows the framework '
                   'to decide,which exactly output file should be used. If '
                   'not specified, resolves the latest deploy name')
@click.option('--bundle_name',
              callback=resolve_default_value,
              help='Name of the bundle to export from. '
                   'Default value: name of the latest built bundle')
@click.option('--output_dir',
              help='The directory where an exported configuration will be '
                   'saved. If not specified, the directory with the name '
                   '"export" will be created in the project root directory to '
                   'store export files')
@verbose_option
def export(resource_type, dsl, deploy_name, bundle_name, output_dir):
    """
    Exports a configuration of the specified resource type to the file in a
    specified DSL

    param: resource_type: the type of the resource
    param: dsl: the DSL of the output configuration
    param: deploy_name: the name of the deployment
    param: bundle_name: the name of the bundle to export from
    param: output_dir: the directory where an exported specification will be
    saved
    """
    export_specification(deploy_name=deploy_name,
                         bundle_name=bundle_name,
                         output_directory=output_dir,
                         resource_type=resource_type,
                         dsl=dsl)
    if resource_type == 'api_gateway' and dsl == 'oas_v3':
        click.secho('Please note the AWS API Gateway-specific extensions are '
                    'used to define the API in OAS v3 that starting with '
                    '"x-amazon"', fg='yellow')


syndicate.add_command(generate)
syndicate.add_command(tags)
