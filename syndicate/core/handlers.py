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
from functools import partial

import click
from tabulate import tabulate

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.export.export_processor import export_specification
from syndicate.core.transform.transform_processor import generate_build_meta
from syndicate.core import initialize_connection, \
    initialize_project_state, initialize_signal_handling
from syndicate.core.build.artifact_processor import RUNTIME_NODEJS, \
    assemble_artifacts, RUNTIME_JAVA, RUNTIME_PYTHON, RUNTIME_SWAGGER_UI, \
    RUNTIME_DOTNET, RUNTIME_APPSYNC
from syndicate.core.build.bundle_processor import create_bundles_bucket, \
    load_bundle, upload_bundle_to_s3, if_bundle_exist, \
    remove_bundle_dir_locally
from syndicate.core.build.deployment_processor import \
    create_deployment_resources, remove_deployment_resources, \
    update_deployment_resources
from syndicate.core.build.meta_processor import create_meta
from syndicate.core.build.profiler_processor import (get_metric_statistics,
                                                     process_metrics)
from syndicate.core.build.warmup_processor import process_deploy_resources, \
    process_api_gw_resources, warm_upper, process_existing_api_gw_id, \
    process_inputted_api_gw_id
from syndicate.core.conf.validator import (JAVA_LANGUAGE_NAME,
                                           PYTHON_LANGUAGE_NAME,
                                           NODEJS_LANGUAGE_NAME,
                                           SWAGGER_UI_NAME,
                                           DOTNET_LANGUAGE_NAME, APPSYNC_NAME)
from syndicate.core.decorators import (check_deploy_name_for_duplicates,
                                       check_deploy_bucket_exists,
                                       check_bundle_deploy_names_for_existence,
                                       return_code_manager)
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
                                   param_to_lower, verbose_option,
                                   validate_incompatible_options,
                                   failed_status_code_on_exception)
from syndicate.core.project_state.project_state import (MODIFICATION_LOCK,
                                                        WARMUP_LOCK)
from syndicate.core.project_state.status_processor import project_state_status
from syndicate.core.project_state.sync_processor import sync_project_state
from syndicate.core.constants import TEST_ACTION, BUILD_ACTION, \
    DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION, SYNC_ACTION, ABORTED_STATUS, \
    STATUS_ACTION, WARMUP_ACTION, PROFILER_ACTION, ASSEMBLE_JAVA_MVN_ACTION, \
    ASSEMBLE_PYTHON_ACTION, ASSEMBLE_NODE_ACTION, ASSEMBLE_ACTION, \
    PACKAGE_META_ACTION, CREATE_DEPLOY_TARGET_BUCKET_ACTION, UPLOAD_ACTION, \
    COPY_BUNDLE_ACTION, EXPORT_ACTION, ASSEMBLE_SWAGGER_UI_ACTION, \
    ASSEMBLE_DOTNET_ACTION, ASSEMBLE_APPSYNC_ACTION, OK_RETURN_CODE, \
    FAILED_RETURN_CODE, ABORTED_RETURN_CODE

INIT_COMMAND_NAME = 'init'
SYNDICATE_PACKAGE_NAME = 'aws-syndicate'
HELP_PARAMETER_KEY = '--help'
commands_without_config = (
    INIT_COMMAND_NAME,
    GENERATE_PROJECT_COMMAND_NAME,
    GENERATE_CONFIG_COMMAND_NAME,
    HELP_PARAMETER_KEY
)

commands_without_state_sync = (
    CREATE_DEPLOY_TARGET_BUCKET_ACTION
)

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def _not_require_config(all_params):
    return any(item in commands_without_config for item in all_params)


def _not_require_state_sync(all_params):
    return any(item in commands_without_state_sync for item in all_params)


@click.group(name='syndicate')
@return_code_manager
@click.version_option()
def syndicate():
    from syndicate.core import CONF_PATH
    if _not_require_config(sys.argv):
        pass
    elif CONF_PATH:
        USER_LOG.info('Configuration used: ' + CONF_PATH)
        initialize_connection()
        initialize_project_state(
            do_not_sync_state=_not_require_state_sync(sys.argv)
        )
        initialize_signal_handling()
    else:
        USER_LOG.error('Environment variable SDCT_CONF is not set! '
                       'Please verify that you have provided path to '
                       'correct config files '
                       'or execute `syndicate generate config` command.')
        sys.exit(FAILED_RETURN_CODE)


@syndicate.command(name=TEST_ACTION)
@return_code_manager
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
@click.option('--skip_tests', is_flag=True, default=False,
              help='Flag to not run tests')
@verbose_option
@timeit(action_name=TEST_ACTION)
@failed_status_code_on_exception
def test(suite, test_folder_name, errors_allowed, skip_tests):
    """Discovers and runs tests inside python project configuration path."""
    if skip_tests:
        USER_LOG.info('Skipping tests...')
        return OK_RETURN_CODE

    USER_LOG.info('Running tests...')
    import subprocess
    from syndicate.core import CONFIG
    project_path = CONFIG.project_path
    test_folder = os.path.join(project_path, test_folder_name)
    if not os.path.exists(test_folder):
        msg = (f'Tests not found, \'{test_folder_name}\' folder is missing in '
               f'\'{project_path}\'.')
        USER_LOG.info(msg)
        return OK_RETURN_CODE
    test_lib_command_mapping = {
        'unittest': f'{sys.executable} -m unittest discover {test_folder} -v',
        'pytest': 'pytest --no-header -v',
        'nose': 'nosetests --verbose'
    }

    command = test_lib_command_mapping.get(suite)
    result = subprocess.run(command, cwd=project_path, shell=True,
                            capture_output=True, text=True)

    if result.returncode != OK_RETURN_CODE:
        _LOG.error(f'{result.stdout}\n{result.stderr}\n{"-" * 70}')
        if not errors_allowed:
            USER_LOG.error(
                'Some tests failed. See details in the log file. Exiting...')
            return result.returncode
        else:
            USER_LOG.warning('Some tests failed. See details in the log file.')
            return OK_RETURN_CODE
    else:
        _LOG.info(f'{result.stdout}\n{result.stderr}\n{"-" * 70}')
        USER_LOG.info('Tests passed.')
        return OK_RETURN_CODE


@syndicate.command(name=BUILD_ACTION)
@return_code_manager
@click.option('--bundle_name', '-b', nargs=1,
              callback=generate_default_bundle_name,
              help='Name of the bundle to build. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%SZ')
@click.option('--force_upload', '-F', is_flag=True, default=False,
              help='Flag to override existing bundle with the same name')
@click.option('--errors_allowed', is_flag=True, default=False,
              help='Flag to continue building the bundle if any errors occur '
                   'while building dependencies or tests fail')
@click.option('--skip_tests', is_flag=True, default=False,
              help='Flag to skip lambda tests')
@verbose_option
@click.pass_context
@timeit(action_name=BUILD_ACTION)
@failed_status_code_on_exception
@check_deploy_bucket_exists
def build(ctx, bundle_name, force_upload, errors_allowed, skip_tests):
    """
    Builds bundle of an application
    """
    if if_bundle_exist(bundle_name=bundle_name) and not force_upload:
        USER_LOG.error(f'Bundle name \'{bundle_name}\' already exists '
                       f'in deploy bucket. Please use another bundle '
                       f'name or delete the bundle')
        return FAILED_RETURN_CODE

    test_code = ctx.invoke(test,
                           errors_allowed=errors_allowed,
                           skip_tests=skip_tests)
    if test_code != OK_RETURN_CODE:
        return test_code

    assemble_code = ctx.invoke(assemble, bundle_name=bundle_name,
                               errors_allowed=errors_allowed,
                               skip_tests=skip_tests,
                               force_upload=force_upload)
    if assemble_code != OK_RETURN_CODE:
        return assemble_code

    meta_code = ctx.invoke(package_meta, bundle_name=bundle_name)
    if meta_code != OK_RETURN_CODE:
        return meta_code

    upload_code = ctx.invoke(upload,
                             bundle_name=bundle_name,
                             force_upload=force_upload)
    return upload_code


@syndicate.command(name='transform')
@return_code_manager
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
    return OK_RETURN_CODE


@syndicate.command(name=DEPLOY_ACTION)
@return_code_manager
@sync_lock(lock_type=MODIFICATION_LOCK)
@timeit(action_name=DEPLOY_ACTION)
@failed_status_code_on_exception
@click.option('--deploy_name', '-d', callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--bundle_name', '-b', callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_only_types', '-types', multiple=True,
              help='Types of the resources to deploy')
@click.option('--deploy_only_resources', '-resources', multiple=True,
              help='Names of the resources to deploy')
@click.option('--deploy_only_resources_path', '-path', nargs=1, type=str,
              help='Path to file containing names of the resources to deploy')
@click.option('--excluded_resources', '-exresources', multiple=True,
              help='Names of the resources to skip while deploy.')
@click.option('--excluded_resources_path', '-expath', nargs=1, type=str,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--excluded_types', '-extypes', multiple=True,
              help='Types of the resources to skip while deploy')
@click.option('--continue_deploy', is_flag=True, default=False,
              help='Flag to continue failed deploy')
@click.option('--replace_output', is_flag=True, default=False,
              help='Flag to replace the existing deploy output')
@click.option('--rollback_on_error', is_flag=True, default=False,
              help='Flag to automatically clean deployed resources if the'
                   ' deployment is unsuccessful')
@verbose_option
@check_deploy_name_for_duplicates
@check_deploy_bucket_exists
@check_bundle_deploy_names_for_existence()
def deploy(
        deploy_name: str,
        bundle_name: str,
        deploy_only_types: tuple | None = None,
        deploy_only_resources: tuple | None = None,
        deploy_only_resources_path: str | None = None,
        excluded_resources: tuple | None = None,
        excluded_resources_path: str | None = None,
        excluded_types: tuple | None = None,
        continue_deploy: bool = False,
        replace_output: bool = False,
        rollback_on_error: bool = False,
):
    """
    Deploys the application infrastructure
    """
    from syndicate.core import PROJECT_STATE
    PROJECT_STATE.current_bundle = bundle_name

    if deploy_only_resources_path and os.path.exists(
            deploy_only_resources_path):
        deploy_resources_list = json.load(open(deploy_only_resources_path))
        deploy_only_resources = tuple(
            set(deploy_only_resources + tuple(deploy_resources_list)))
        if deploy_only_resources:
            USER_LOG.info(
                f'Resources to deploy: {list(deploy_only_resources)}')

    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))
        if excluded_resources:
            USER_LOG.info(f'Resources to deploy: {list(excluded_resources)}')

    deploy_success = create_deployment_resources(
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        deploy_only_types=deploy_only_types,
        deploy_only_resources=deploy_only_resources,
        excluded_resources=excluded_resources,
        excluded_types=excluded_types,
        continue_deploy=continue_deploy,
        replace_output=replace_output,
        rollback_on_error=rollback_on_error,
    )

    message = 'Backend resources were deployed{suffix}.'.format(
        suffix='' if deploy_success else (
            ' with errors. Rollback is enabled, resources from this '
            'deployment were cleaned'
            if rollback_on_error else ' with errors. See deploy output file'
        )
    )

    if not deploy_success:
        USER_LOG.warning(message)
        return FAILED_RETURN_CODE

    USER_LOG.info(message)
    return OK_RETURN_CODE


@syndicate.command(name=UPDATE_ACTION)
@return_code_manager
@sync_lock(lock_type=MODIFICATION_LOCK)
@timeit(action_name=UPDATE_ACTION)
@failed_status_code_on_exception
@click.option('--bundle_name', '-b', callback=resolve_default_value,
              help='Name of the bundle to deploy. '
                   'Default value: name of the latest built bundle')
@click.option('--deploy_name', '-d', callback=resolve_default_value,
              help='Name of the deploy. Default value: name of the project')
@click.option('--update_only_types', '-types', multiple=True,
              help='Types of the resources to update')
@click.option('--update_only_resources', '-resources', multiple=True,
              help='Names of the resources to update')
@click.option('--update_only_resources_path', '-path', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while deploy')
@click.option('--excluded_resources', '-exresources', multiple=True,
              help='Names of the resources to skip while update.')
@click.option('--excluded_resources_path', '-expath', nargs=1,
              help='Path to file containing names of the resources to skip '
                   'while update')
@click.option('--excluded_types', '-extypes', multiple=True,
              help='Types of the resources to skip while update')
@click.option('--replace_output', nargs=1, is_flag=True, default=False,
              help='The flag to replace the existing deploy output file')
@click.option('--force', nargs=1, is_flag=True, default=False,
              help='The flag, to apply updates even if the latest deployment '
                   'failed')
@verbose_option
@check_deploy_name_for_duplicates
@check_deploy_bucket_exists
@check_bundle_deploy_names_for_existence()
def update(
        bundle_name: str,
        deploy_name: str,
        update_only_types: tuple | None = None,
        update_only_resources: tuple | None = None,
        update_only_resources_path: str | None = None,
        excluded_resources: tuple | None = None,
        excluded_resources_path: str | None = None,
        excluded_types: tuple | None = None,
        replace_output: bool = False,
        force: bool = False,
):
    """
    Updates infrastructure from the provided bundle
    """
    from syndicate.core import PROJECT_STATE
    USER_LOG.info(f'Bundle name: {bundle_name}')
    PROJECT_STATE.current_bundle = bundle_name

    if update_only_resources_path and os.path.exists(
            update_only_resources_path):
        update_resources_list = json.load(open(update_only_resources_path))
        update_only_resources = tuple(
            set(update_only_resources + tuple(update_resources_list)))
        if update_only_resources:
            USER_LOG.info(
                f'Resources to update: {list(update_only_resources)}')

    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))
        if excluded_resources:
            USER_LOG.info(
                f'Resources excluded from update: {list(excluded_resources)}')

    success = update_deployment_resources(
        bundle_name=bundle_name,
        deploy_name=deploy_name,
        update_only_types=update_only_types,
        update_only_resources=update_only_resources,
        excluded_resources=excluded_resources,
        excluded_types=excluded_types,
        replace_output=replace_output,
        force=force)
    if success is True:
        USER_LOG.info('Update of resources has been successfully completed')
        return OK_RETURN_CODE
    elif success == ABORTED_STATUS:
        USER_LOG.warning('Update of resources has been aborted')
        # not ABORTED_RETURN_CODE because of event status in .syndicate file
        return FAILED_RETURN_CODE
    else:
        USER_LOG.warning('Something went wrong during resources update')
        return FAILED_RETURN_CODE


@syndicate.command(name=CLEAN_ACTION)
@return_code_manager
@sync_lock(lock_type=MODIFICATION_LOCK)
@timeit(action_name=CLEAN_ACTION)
@failed_status_code_on_exception
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
@click.option('--preserve_state', is_flag=True,
              help='Preserve deploy output json file after resources removal')
@verbose_option
@check_bundle_deploy_names_for_existence(check_deploy_existence=True)
def clean(
        deploy_name: str,
        bundle_name: str,
        clean_only_types: tuple | None = None,
        clean_only_resources: tuple | None = None,
        clean_only_resources_path: str | None = None,
        clean_externals: bool = False,
        excluded_resources: tuple | None = None,
        excluded_resources_path: str | None = None,
        excluded_types: tuple | None = None,
        preserve_state: bool = False,
):
    """
    Cleans the application infrastructure
    """
    from syndicate.core import PROJECT_STATE
    USER_LOG.info('Command clean')
    USER_LOG.info(f'Deploy name: {deploy_name}')
    separator = ', '
    PROJECT_STATE.current_bundle = bundle_name

    if clean_only_types:
        USER_LOG.info(f'Clean only types: {separator.join(clean_only_types)}')
    if clean_only_resources:
        USER_LOG.info(f'Clean only resources: '
                   f'{separator.join(clean_only_resources)}')
    if clean_only_resources_path:
        USER_LOG.info(f'Clean only resources path: {clean_only_resources_path}')
    if excluded_resources:
        USER_LOG.info(f'Excluded resources: {separator.join(excluded_resources)}')
    if excluded_resources_path:
        USER_LOG.info(f'Excluded resources path: {excluded_resources_path}')
    if excluded_types:
        USER_LOG.info(f'Excluded types: {separator.join(excluded_resources)}')
    if clean_only_resources_path and os.path.exists(clean_only_resources_path):
        clean_resources_list = json.load(open(clean_only_resources_path))
        clean_only_resources = tuple(
            set(clean_only_resources + tuple(clean_resources_list)))
    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))

    result = remove_deployment_resources(
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        clean_only_resources=clean_only_resources,
        clean_only_types=clean_only_types,
        excluded_resources=excluded_resources,
        excluded_types=excluded_types,
        clean_externals=clean_externals,
        preserve_state=preserve_state)

    if result == ABORTED_STATUS:
        USER_LOG.warning('Clean of resources has been aborted')
        return ABORTED_RETURN_CODE
    elif result is False:
        USER_LOG.warning('AWS resources were removed with errors.')
        return FAILED_RETURN_CODE
    elif isinstance(result, dict) and 'operation' in result:
        USER_LOG.info('AWS resources were removed.')
        return {**result, 'return_code': OK_RETURN_CODE}
    else:
        USER_LOG.info('AWS resources were removed.')
    return OK_RETURN_CODE


@syndicate.command(name=SYNC_ACTION)
@return_code_manager
@timeit()
@verbose_option
@check_deploy_bucket_exists
def sync():
    """
    Syncs the state of local project state file (.syndicate) and
    the remote one.
    """
    sync_project_state()
    return OK_RETURN_CODE


@syndicate.command(name=STATUS_ACTION)
@return_code_manager
@click.option('--events', flag_value='events',
              callback=partial(validate_incompatible_options,
                               incompatible_options=['resources']),
              help='Show event logs of the project')
@click.option('--resources', flag_value='resources',
              callback=partial(validate_incompatible_options,
                               incompatible_options=['events']),
              help='Show a summary of the project resources')
@verbose_option
@timeit()
@check_deploy_bucket_exists
def status(events, resources):
    """
    Shows the state of a local project state file (.syndicate).
    Command displays the following content: project name, state, latest
    modification, locks summary, latest event, project resources.
    """
    click.echo(project_state_status(category=events or resources))
    return OK_RETURN_CODE


@syndicate.command(name=WARMUP_ACTION)
@return_code_manager
@sync_lock(lock_type=WARMUP_LOCK)
@timeit(action_name=WARMUP_ACTION)
@failed_status_code_on_exception
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
@check_bundle_deploy_names_for_existence()
def warmup(bundle_name, deploy_name, api_gw_id, stage_name, lambda_auth,
           header_name, header_value):
    """
    Warmups Lambda functions
    """
    if bundle_name and deploy_name:
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_deploy_resources(deploy_name=deploy_name,
                                     bundle_name=bundle_name)
    elif api_gw_id:
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_inputted_api_gw_id(api_id=api_gw_id, stage_name=stage_name)
    else:
        paths_to_be_triggered, resource_path_warmup_key_mapping = \
            process_existing_api_gw_id(stage_name=stage_name)

    if not paths_to_be_triggered or not resource_path_warmup_key_mapping:
        USER_LOG.info('No resources to warm up')
        return OK_RETURN_CODE
    resource_method_mapping, resource_warmup_key_mapping = \
        process_api_gw_resources(paths_to_be_triggered=paths_to_be_triggered,
                                 resource_path_warmup_key_mapping=
                                 resource_path_warmup_key_mapping)
    warm_upper(resource_method_mapping=resource_method_mapping,
               resource_warmup_key_mapping=resource_warmup_key_mapping,
               lambda_auth=lambda_auth, header_name=header_name,
               header_value=header_value)
    USER_LOG.info('Application resources have been warmed up.')
    return OK_RETURN_CODE


@syndicate.command(name=PROFILER_ACTION)
@return_code_manager
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
@check_bundle_deploy_names_for_existence(check_deploy_existence=True)
def profiler(bundle_name, deploy_name, from_date, to_date):
    """
    Displays application Lambda metrics
    """

    metric_value_dict = get_metric_statistics(bundle_name, deploy_name,
                                              from_date, to_date)
    for lambda_name, metrics in metric_value_dict.items():
        prettify_metrics_dict = {}

        USER_LOG.info(f'{os.linesep}Lambda function name: {lambda_name}')
        prettify_metrics_dict = process_metrics(prettify_metrics_dict, metrics)
        if not prettify_metrics_dict:
            USER_LOG.warning('No executions found')
        USER_LOG.info(tabulate(prettify_metrics_dict, headers='keys',
                               stralign='right'))
    return OK_RETURN_CODE


# =============================================================================


@syndicate.command(name=ASSEMBLE_JAVA_MVN_ACTION)
@return_code_manager
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
@click.option('--force_upload', '-fu', nargs=1,
              default=False, required=False,
              help='Identifier that indicates whether a locally existing'
                   ' bundle should be deleted and a new one created using'
                   ' the same path.')
@click.option('--skip_tests', is_flag=True, default=False,
              help='Flag to not run tests')
@click.option('--errors_allowed', is_flag=True, default=False,
              help='Flag to continue building the bundle in case of errors '
                   'while building artifacts')
@verbose_option
@timeit(action_name=ASSEMBLE_JAVA_MVN_ACTION)
@failed_status_code_on_exception
def assemble_java_mvn(bundle_name, project_path, force_upload, skip_tests,
                      errors_allowed):
    """
    Builds Java lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :param force_upload: force upload identification
    :param skip_tests: force skipping tests
    :param errors_allowed: not used for java, but need to unify the
    `assemble` commands interface
    :return:
    """
    USER_LOG.info(f'Command compile java project path: {project_path}')
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        remove_bundle_dir_locally(bundle_name)

    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_JAVA,
                       skip_tests=skip_tests,
                       errors_allowed=errors_allowed)
    USER_LOG.info('Java artifacts were prepared successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=ASSEMBLE_PYTHON_ACTION)
@return_code_manager
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
@click.option('--force_upload', '-fu', nargs=1,
              default=False, required=False,
              help='Identifier that indicates whether a locally existing'
                   ' bundle should be deleted and a new one created using'
                   ' the same path.')
@click.option('--errors_allowed', is_flag=True, default=False,
              help='Flag to continue building the bundle if any errors occur '
                   'while building dependencies')
@verbose_option
@timeit(action_name=ASSEMBLE_PYTHON_ACTION)
@failed_status_code_on_exception
def assemble_python(bundle_name, project_path, force_upload, errors_allowed,
                    skip_tests=False):
    """
    Builds Python lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :param force_upload: force upload identification
    :param errors_allowed: allows to ignore dependency errors
    :param skip_tests: not used for python, but need to unify the
    `assemble` commands interface
    :return:
    """
    USER_LOG.info(f'Command assemble python: project_path: {project_path} ')
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        remove_bundle_dir_locally(bundle_name)

    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_PYTHON,
                       errors_allowed=errors_allowed)
    USER_LOG.info('Python artifacts were prepared successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=ASSEMBLE_NODE_ACTION)
@return_code_manager
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
@click.option('--force_upload', '-fu', nargs=1,
              default=False, required=False,
              help='Identifier that indicates whether a locally existing'
                   ' bundle should be deleted and a new one created using'
                   ' the same path.')
@verbose_option
@timeit(action_name=ASSEMBLE_NODE_ACTION)
@failed_status_code_on_exception
def assemble_node(bundle_name, project_path, force_upload,
                  errors_allowed=False, skip_tests=False):
    """
    Builds NodeJS lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :param force_upload: force upload identification
    :param errors_allowed: not used for NodeJS, but need to unify the
    `assemble` commands interface
    :param skip_tests: not used for NodeJS, but need to unify the
    `assemble` commands interface
    :return:
    """
    USER_LOG.info(f'Command assemble node: project_path: {project_path} ')
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        remove_bundle_dir_locally(bundle_name)

    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_NODEJS)
    USER_LOG.info('NodeJS artifacts were prepared successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=ASSEMBLE_DOTNET_ACTION)
@return_code_manager
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
@click.option('--force_upload', '-fu', nargs=1,
              default=False, required=False,
              help='Identifier that indicates whether a locally existing'
                   ' bundle should be deleted and a new one created using'
                   ' the same path.')
@verbose_option
@timeit(action_name=ASSEMBLE_DOTNET_ACTION)
@failed_status_code_on_exception
def assemble_dotnet(bundle_name, project_path, force_upload,
                    errors_allowed=False, skip_tests=False):
    """
    Builds DotNet lambdas

    \f
    :param bundle_name: name of the bundle
    :param project_path: path to project folder
    :param force_upload: force upload identification
    :param errors_allowed: not used for DotNet, but need to unify the
    `assemble` commands interface
    :param skip_tests: not used for DotNet, but need to unify the
    `assemble` commands interface
    :return:
    """
    USER_LOG.info(f'Command assemble dotnet: project_path: {project_path} ')
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        remove_bundle_dir_locally(bundle_name)

    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_DOTNET)
    USER_LOG.info('DotNet artifacts were prepared successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=ASSEMBLE_SWAGGER_UI_ACTION)
@return_code_manager
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
@failed_status_code_on_exception
def assemble_swagger_ui(**kwargs):
    """
        Builds Swagger UI artifacts

        \f
        :param bundle_name: name of the bundle
        :param project_path: path to project folder
        :return:
        """
    bundle_name = kwargs.get('bundle_name')
    project_path = kwargs.get('project_path')
    USER_LOG.info(f'Command assemble Swagger UI: project_path: {project_path} ')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_SWAGGER_UI)
    USER_LOG.info('Swagger UI artifacts were prepared successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=ASSEMBLE_APPSYNC_ACTION)
@return_code_manager
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
@timeit(action_name=ASSEMBLE_APPSYNC_ACTION)
@failed_status_code_on_exception
def assemble_appsync(**kwargs):
    """
        Builds AppSync artifacts

        \f
        :param bundle_name: name of the bundle
        :param project_path: path to project folder
        :return:
        """
    bundle_name = kwargs.get('bundle_name')
    project_path = kwargs.get('project_path')
    USER_LOG.info(f'Command assemble AppSync: project_path: {project_path} ')
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_APPSYNC)
    USER_LOG.info('AppSync artifacts were prepared successfully.')
    return OK_RETURN_CODE


RUNTIME_LANG_TO_BUILD_MAPPING = {
    JAVA_LANGUAGE_NAME: assemble_java_mvn,
    PYTHON_LANGUAGE_NAME: assemble_python,
    NODEJS_LANGUAGE_NAME: assemble_node,
    DOTNET_LANGUAGE_NAME: assemble_dotnet,
    SWAGGER_UI_NAME: assemble_swagger_ui,
    APPSYNC_NAME: assemble_appsync
}


@syndicate.command(name=ASSEMBLE_ACTION)
@return_code_manager
@click.option('--bundle_name', '-b', callback=generate_default_bundle_name,
              help='Bundle\'s name to build the lambdas in. '
                   'Default value: $ProjectName_%Y%m%d.%H%M%S')
@click.option('--force_upload', '-fu', nargs=1,
              default=False, required=False,
              help='Identifier that indicates whether a locally existing'
                   ' bundle should be deleted and a new one created using'
                   ' the same path.')
@click.option('--errors_allowed', is_flag=True, default=False,
              help='Flag to continue building the bundle if any errors occur '
                   'while building dependencies. Only for Python runtime.')
@verbose_option
@click.pass_context
@timeit(action_name=ASSEMBLE_ACTION)
@failed_status_code_on_exception
def assemble(ctx, bundle_name, force_upload, errors_allowed, skip_tests=False):
    """
    Builds the application artifacts

    \f
    :param ctx:
    :param bundle_name: name of the bundle to which the artifacts
        will be associated
    :param force_upload: force upload identification
    :param errors_allowed: allows to ignore errors.
    :param skip_tests: allows to skip tests
    :return:
    """
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        remove_bundle_dir_locally(bundle_name)

    USER_LOG.info(f'Building artifacts, bundle: {bundle_name}')
    from syndicate.core import PROJECT_STATE
    # Updates stale state aggregation
    PROJECT_STATE.refresh_state()

    build_mapping_dict: dict = PROJECT_STATE.load_project_build_mapping()
    if build_mapping_dict:
        for key, value in build_mapping_dict.items():
            func = RUNTIME_LANG_TO_BUILD_MAPPING.get(key)
            if func:
                return_code = ctx.invoke(func, bundle_name=bundle_name,
                                         project_path=value,
                                         force_upload=False, # because we have already deleted the bundle folder
                                         errors_allowed=errors_allowed,
                                         skip_tests=skip_tests)
                if return_code != OK_RETURN_CODE:
                    return return_code
            else:
                USER_LOG.error(f'Build tool is not supported: {key}')
                return FAILED_RETURN_CODE
    else:
        USER_LOG.info(
            'Resources for which artifacts need to be built were not found'
        )
    return OK_RETURN_CODE


@syndicate.command(name=PACKAGE_META_ACTION)
@return_code_manager
@click.option('--bundle_name', '-b', required=True,
              callback=verify_bundle_callback,
              help='Bundle\'s name to package the current meta in')
@verbose_option
@timeit(action_name=PACKAGE_META_ACTION)
@failed_status_code_on_exception
def package_meta(bundle_name):
    """
    Generates metadata about the application infrastructure

    \f
    :param bundle_name: name of the bundle to generate metadata
    :return:
    """
    from syndicate.core import CONFIG
    USER_LOG.info(f'Package meta, bundle: {bundle_name}')
    create_meta(project_path=CONFIG.project_path,
                bundle_name=bundle_name)
    USER_LOG.info('Meta was configured successfully.')
    return OK_RETURN_CODE


@syndicate.command(name=CREATE_DEPLOY_TARGET_BUCKET_ACTION)
@return_code_manager
@verbose_option
@timeit()
def create_deploy_target_bucket():
    """
    Creates a bucket in AWS account where all bundles will be uploaded
    """
    from syndicate.core import CONFIG
    USER_LOG.info(f'Create deploy target bucket: {CONFIG.deploy_target_bucket}')
    result = create_bundles_bucket()
    if not result:
        return ABORTED_RETURN_CODE
    USER_LOG.info('Deploy target bucket was created successfully')
    return OK_RETURN_CODE


@syndicate.command(name=UPLOAD_ACTION)
@return_code_manager
@click.option('--bundle_name', '-b',
              callback=resolve_and_verify_bundle_callback,
              help='Bundle name to which the build artifacts are gathered '
                   'and later used for the deployment. NOTE: if not '
                   'specified, the latest build will be uploaded')
@click.option('--force_upload', '-F', is_flag=True,
              help='Flag to override existing bundle with the same name as '
                   'provided')
@verbose_option
@timeit(action_name=UPLOAD_ACTION)
@failed_status_code_on_exception
@check_deploy_bucket_exists
def upload(bundle_name, force_upload=False):
    """
    Uploads bundle from local storage to AWS S3

    \f
    :param bundle_name: name of the bundle to upload
    :param force_upload: used if the bundle with the same name as provided
        already exists in an account
    :return:
    """
    USER_LOG.info(f'Upload bundle: {bundle_name}')
    if force_upload:
        USER_LOG.info('Force upload')

    futures = upload_bundle_to_s3(bundle_name=bundle_name, force=force_upload)
    handle_futures_progress_bar(futures)

    USER_LOG.info('Bundle was uploaded successfully')
    return OK_RETURN_CODE


@syndicate.command(name=COPY_BUNDLE_ACTION)
@return_code_manager
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
    USER_LOG.info(f'Copy bundle: {bundle_name}')
    USER_LOG.info(f'Bundle name: {bundle_name}')
    USER_LOG.info(f'Source account id: {src_account_id}')
    USER_LOG.info(f'Source bucket region: {src_bucket_region}')
    USER_LOG.info(f'Source bucket name: {src_bucket_name}')
    futures = load_bundle(bundle_name, src_account_id, src_bucket_region,
                          src_bucket_name, role_name)
    handle_futures_progress_bar(futures)
    USER_LOG.info('Bundle was downloaded successfully')
    ctx.invoke(upload, bundle_name=bundle_name, force=force_upload)
    USER_LOG.info('Bundle was copied successfully')
    return OK_RETURN_CODE


@syndicate.command(name=EXPORT_ACTION)
@return_code_manager
@click.option('--resource_type', '-rt', required=True,
              type=click.Choice(['api_gateway']),
              help='The type of resource to export configuration')
@click.option('--dsl', default='oas_v3',
              type=click.Choice(['oas_v3']),
              help='DSL of output specification. Default: oas_v3')
@click.option('--deploy_name', '-d', nargs=1, callback=resolve_default_value,
              help='Name of the deploy. This parameter allows the framework '
                   'to decide, which exactly output file should be used. If '
                   'not specified, resolves the latest deploy name')
@click.option('--bundle_name', '-b', callback=resolve_default_value,
              help='Name of the bundle to export from. Default value: name of '
                   'the latest built bundle')
@click.option('--output_dir', '-od',
              help='The directory where an exported configuration will be '
                   'saved. If not specified, the directory with the name '
                   '"export" will be created in the project root directory to '
                   'store export files')
@verbose_option
def export(
        resource_type: str,
        dsl: str,
        deploy_name: str,
        bundle_name: str,
        output_dir: str | None = None,
):
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
    export_specification(
        resource_type=resource_type,
        dsl=dsl,
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        output_directory=output_dir,
    )
    if resource_type == 'api_gateway' and dsl == 'oas_v3':
        USER_LOG.info(
            'Please note the AWS API Gateway-specific extensions are '
            'used to define the API in OAS v3 that starting with '
            '"x-amazon"'
        )
    return OK_RETURN_CODE


syndicate.add_command(generate)
syndicate.add_command(tags)
