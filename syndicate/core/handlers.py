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

from syndicate.core import CONF_PATH, initialize_connection, \
    initialize_project_state
from syndicate.core.build.artifact_processor import (RUNTIME_NODEJS,
                                                     assemble_artifacts,
                                                     RUNTIME_JAVA_8,
                                                     RUNTIME_PYTHON)
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
                                           NODEJS_LANGUAGE_NAME)
from syndicate.core.decorators import check_deploy_name_for_duplicates
from syndicate.core.groups.generate import generate, GENERATE_GROUP_NAME
from syndicate.core.helper import (check_required_param,
                                   create_bundle_callback,
                                   handle_futures_progress_bar,
                                   resolve_path_callback, timeit,
                                   verify_bundle_callback,
                                   verify_meta_bundle_callback,
                                   resolve_default_value,
                                   generate_default_bundle_name,
                                   sync_lock)
from syndicate.core.project_state.project_state import (MODIFICATION_LOCK,
                                                        WARMUP_LOCK)
from syndicate.core.project_state.status_processor import project_state_status
from syndicate.core.project_state.sync_processor import sync_project_state

INIT_COMMAND_NAME = 'init'
commands_without_config = (
    INIT_COMMAND_NAME,
    GENERATE_GROUP_NAME
)


def _not_require_config(all_params):
    return any(item in commands_without_config for item in all_params)


@click.group(name='syndicate')
@click.version_option()
def syndicate():
    if CONF_PATH:
        click.echo('Configuration used: ' + CONF_PATH)
        initialize_connection()
        initialize_project_state()
    elif _not_require_config(sys.argv):
        pass
    else:
        click.echo('Environment variable SDCT_CONF is not set! '
                   'Please verify that you configured have provided path to '
                   'correct config files '
                   'or execute `syndicate generate config` command.')
        sys.exit(1)


@syndicate.command(name='test')
@click.option('--suite', type=click.Choice(['unittest', 'pytest', 'nose'],
                                           case_sensitive=False),
              default='unittest')
@click.option('--test_folder_name', nargs=1, default='tests')
@timeit()
def test(suite, test_folder_name):
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
        'unittest': 'python -m unittest -v',
        'pytest': 'pytest --no-header -v',
        'nose': 'nosetests --verbose'
    }

    workdir = os.getcwd()

    os.chdir(os.path.join(test_folder, '..'))
    command = test_lib_command_mapping.get(suite)
    result = subprocess.run(command.split())

    os.chdir(workdir)
    if result.returncode != 0:
        click.echo('Some tests failed. Exiting.')
        sys.exit(1)


@syndicate.command(name='build')
@click.option('--bundle_name', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle to build. '
                   'Default value: $ProjectName_%Y-%m-%dT%H:%M:%SZ')
@click.option('--force_upload', is_flag=True, default=False,
              help='Flag to override existing bundle with the same name')
@click.pass_context
@timeit(action_name='build')
def build(ctx, bundle_name, force_upload):
    """
    Builds bundle of an application
    """
    if if_bundle_exist(bundle_name=bundle_name) and not force_upload:
        click.echo('Bundle name \'{0}\' already exists '
                   'in deploy bucket. Please use another bundle '
                   'name or delete the bundle'.format(bundle_name))
        return
    ctx.invoke(test)
    ctx.invoke(assemble, bundle_name=bundle_name)
    ctx.invoke(package_meta, bundle_name=bundle_name)
    ctx.invoke(upload, bundle_name=bundle_name, force=force_upload)


@syndicate.command(name='deploy')
@click.option('--deploy_name',
              callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--bundle_name',
              callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_only_types', multiple=True,
              help='Types of the resources to deploy')
@click.option('--deploy_only_resources', multiple=True,
              help='Names of the resources to deploy')
@click.option('--deploy_only_resources_path', nargs=1,
              help='Path to file containing names of the resources to deploy')
@click.option('--excluded_resources', multiple=True,
              help='Names of the resources to skip while deploy.')
@click.option('--excluded_resources_path', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--excluded_types', multiple=True,
              help='Types of the resources to skip while deploy')
@click.option('--continue_deploy', is_flag=True,
              help='Flag to continue failed deploy')
@click.option('--replace_output', is_flag=True, default=False,
              help='Replaces the existing deploy output')
@check_deploy_name_for_duplicates
@sync_lock(lock_type=MODIFICATION_LOCK)
@timeit(action_name='deploy')
def deploy(deploy_name, bundle_name, deploy_only_types, deploy_only_resources,
           deploy_only_resources_path, excluded_resources,
           excluded_resources_path, excluded_types, continue_deploy,
           replace_output):
    """
    Deploys the application infrastructure
    """
    sync_project_state()
    from syndicate.core import PROJECT_STATE
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
    PROJECT_STATE.release_lock(MODIFICATION_LOCK)
    sync_project_state()


@syndicate.command(name='update')
@click.option('--bundle_name',
              callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_name',
              callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--update_only_types', multiple=True,
              help='Types of the resources to update')
@click.option('--update_only_resources', multiple=True,
              help='Names of the resources to deploy')
@click.option('--update_only_resources_path', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--replace_output', nargs=1, is_flag=True, default=False)
@check_deploy_name_for_duplicates
@timeit(action_name='update')
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
        click.echo('Resources to update: {}'.format(list(update_only_resources)))
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


@syndicate.command(name='clean')
@timeit(action_name='clean')
@click.option('--deploy_name', nargs=1, callback=resolve_default_value)
@click.option('--bundle_name', nargs=1, callback=resolve_default_value)
@click.option('--clean_only_types', multiple=True)
@click.option('--clean_only_resources', multiple=True)
@click.option('--clean_only_resources_path', nargs=1, type=str)
@click.option('--clean_externals', nargs=1, is_flag=True, default=False)
@click.option('--excluded_resources', multiple=True)
@click.option('--excluded_resources_path', nargs=1, type=str)
@click.option('--excluded_types', multiple=True)
@click.option('--rollback', is_flag=True)
def clean(deploy_name, bundle_name, clean_only_types, clean_only_resources,
          clean_only_resources_path, clean_externals, excluded_resources,
          excluded_resources_path, excluded_types, rollback):
    """
    Cleans the application infrastructure.
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
        remove_failed_deploy_resources(deploy_name=deploy_name,
                                       bundle_name=bundle_name,
                                       clean_only_resources=clean_only_resources,
                                       clean_only_types=clean_only_types,
                                       excluded_resources=excluded_resources,
                                       excluded_types=excluded_types,
                                       clean_externals=clean_externals)
    else:
        remove_deployment_resources(deploy_name=deploy_name,
                                    bundle_name=bundle_name,
                                    clean_only_resources=clean_only_resources,
                                    clean_only_types=clean_only_types,
                                    excluded_resources=excluded_resources,
                                    excluded_types=excluded_types,
                                    clean_externals=clean_externals)
    click.echo('AWS resources were removed.')


@syndicate.command(name='sync')
@timeit()
def sync():
    """
    Syncs the state of local project state file (.syndicate) and
    the remote one.
    """
    return sync_project_state()


@syndicate.command(name='status')
@click.option('--events', 'category', flag_value='events',
              help='Show event logs of the project')
@click.option('--resources', 'category', flag_value='resources',
              help='Show a summary of the project resources')
@timeit()
def status(category):
    """
    Shows the state of a local project state file (.syndicate).
    """
    click.echo(project_state_status(category))


@syndicate.command(name='warmup')
@click.option('--bundle_name', nargs=1, callback=resolve_default_value,
              help='Name of the bundle. Should be specified with deploy_name'
                   ' parameter.')
@click.option('--deploy_name', nargs=1, callback=resolve_default_value,
              help='Name of the deploy.')
@click.option('--api_gw_id', nargs=1, multiple=True, type=str,
              help='Provide API Gateway IDs to warmup.')
@click.option('--stage_name', nargs=1, multiple=True, type=str,
              help='Name of stages of provided API Gateway IDs.')
@click.option('--lambda_auth', default=False, is_flag=True,
              help='Should be specified if API Gateway Lambda Authorizer is '
                   'enabled')
@click.option('--header_name', nargs=1, help='Name of authentication header.')
@click.option('--header_value', nargs=1, help='Name of authentication header '
                                              'value.')
@sync_lock(lock_type=WARMUP_LOCK)
@timeit(action_name='warmup')
def warmup(bundle_name, deploy_name, api_gw_id, stage_name, lambda_auth,
           header_name, header_value):
    """
    Warmups Lambda functions.
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

    resource_method_mapping, resource_warmup_key_mapping = \
        process_api_gw_resources(paths_to_be_triggered=paths_to_be_triggered,
                                 resource_path_warmup_key_mapping=
                                 resource_path_warmup_key_mapping)
    warm_upper(resource_method_mapping=resource_method_mapping,
               resource_warmup_key_mapping=resource_warmup_key_mapping,
               lambda_auth=lambda_auth, header_name=header_name,
               header_value=header_value)
    click.echo('Application resources have been warmed up.')


@syndicate.command(name='profiler')
@click.option('--bundle_name', nargs=1, callback=resolve_default_value)
@click.option('--deploy_name', nargs=1, callback=resolve_default_value)
@click.option('--from_date', nargs=1, type=str)
@click.option('--to_date', nargs=1, type=str)
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


@syndicate.command(name='assemble_java_mvn')
@timeit()
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_java_mvn(bundle_name, project_path):
    """
    Builds Java lambdas
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo('Command compile java project path: %s' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_JAVA_8)
    click.echo('Java artifacts were prepared successfully.')


@syndicate.command(name='assemble_python')
@timeit()
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_python(bundle_name, project_path):
    """
    Builds Python lambdas
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo('Command assemble python: project_path: %s ' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_PYTHON)
    click.echo('Python artifacts were prepared successfully.')


@syndicate.command(name='assemble_node')
@timeit()
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_node(bundle_name, project_path):
    """
    Builds NodeJS lambdas
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :return:
    """
    click.echo('Command assemble node: project_path: %s ' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_NODEJS)
    click.echo('NodeJS artifacts were prepared successfully.')


RUNTIME_LANG_TO_BUILD_MAPPING = {
    JAVA_LANGUAGE_NAME: assemble_java_mvn,
    PYTHON_LANGUAGE_NAME: assemble_python,
    NODEJS_LANGUAGE_NAME: assemble_node
}


@syndicate.command(name='assemble')
@timeit()
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.pass_context
def assemble(ctx, bundle_name):
    """
    Builds the application artifacts
    :param ctx:
    :param bundle_name: name of the bundle to which the artifacts
        will be associated
    :return:
    """
    click.echo('Building artifacts ...')
    from syndicate.core import PROJECT_STATE
    build_mapping_dict = PROJECT_STATE.load_project_build_mapping()
    if build_mapping_dict:
        for key, value in build_mapping_dict.items():
            func = RUNTIME_LANG_TO_BUILD_MAPPING.get(key)
            if func:
                ctx.invoke(func, bundle_name=bundle_name,
                           project_path=value)
            else:
                click.echo('Build tool is not supported: %s' % key)
    else:
        click.echo('Projects to be built are not found')


@syndicate.command(name='package_meta')
@timeit()
@click.option('--bundle_name', nargs=1, callback=verify_bundle_callback)
def package_meta(bundle_name):
    """
    Generates metadata about the application infrastructure
    :param bundle_name: name of the bundle to generate metadata
    :return:
    """
    from syndicate.core import CONFIG
    click.echo('Package meta, bundle: %s' % bundle_name)
    create_meta(project_path=CONFIG.project_path,
                bundle_name=bundle_name)
    click.echo('Meta was configured successfully.')


@syndicate.command(name='create_deploy_target_bucket')
@timeit()
def create_deploy_target_bucket():
    """
    Creates a bucket in AWS account where all bundles will be uploaded
    :return:
    """
    from syndicate.core import CONFIG
    click.echo('Create deploy target sdk: %s' % CONFIG.deploy_target_bucket)
    create_bundles_bucket()
    click.echo('Deploy target bucket was created successfully')


@syndicate.command(name='upload')
@click.option('--bundle_name', nargs=1, callback=verify_meta_bundle_callback)
@click.option('--force', is_flag=True)
@timeit(action_name='upload')
def upload(bundle_name, force=False):
    """
    Uploads bundle from local storage to AWS S3
    :param bundle_name: name of the bundle to upload
    :param force: used if the bundle with the same name as provided
        already exists in an account
    :return:
    """
    click.echo('Upload bundle: %s' % bundle_name)
    if force:
        click.echo('Force upload')

    futures = upload_bundle_to_s3(bundle_name=bundle_name, force=force)
    handle_futures_progress_bar(futures)

    click.echo('Bundle was uploaded successfully')


@syndicate.command(name='copy_bundle')
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--src_account_id', '-acc_id', nargs=1,
              callback=check_required_param)
@click.option('--src_bucket_region', '-r', nargs=1,
              callback=check_required_param)
@click.option('--src_bucket_name', '-bucket_name', nargs=1,
              callback=check_required_param)
@click.option('--role_name', '-role', nargs=1,
              callback=check_required_param)
@click.option('--force_upload', is_flag=True, default=False)
@timeit()
@click.pass_context
def copy_bundle(ctx, bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name, force_upload):
    """
    Copies the bundle from the specified account-region-bucket to
        account-region-bucket specified in sdct.conf
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
    click.echo('Copy bundle: %s' % bundle_name)
    click.echo('Bundle name: %s' % bundle_name)
    click.echo('Source account id: %s' % src_account_id)
    click.echo('Source bucket region: %s' % src_bucket_region)
    click.echo('Source bucket name: %s' % src_bucket_name)
    futures = load_bundle(bundle_name, src_account_id, src_bucket_region,
                          src_bucket_name, role_name)
    handle_futures_progress_bar(futures)
    click.echo('Bundle was downloaded successfully')
    ctx.invoke(upload, bundle_name=bundle_name, force=force_upload)
    click.echo('Bundle was copied successfully')


syndicate.add_command(generate)
