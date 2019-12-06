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

import click

from syndicate.core import CONFIG, CONF_PATH
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
from syndicate.core.conf.config_holder import (MVN_BUILD_TOOL_NAME,
                                               PYTHON_BUILD_TOOL_NAME,
                                               NODE_BUILD_TOOL_NAME)
from syndicate.core.helper import (check_required_param,
                                   create_bundle_callback,
                                   handle_futures_progress_bar,
                                   resolve_path_callback, timeit,
                                   verify_bundle_callback,
                                   verify_meta_bundle_callback,
                                   check_deploy_name_for_duplicates)


# TODO - command descriptions


@click.group(name='syndicate')
def syndicate():
    click.echo('Path to sdct.conf: ' + CONF_PATH)


# =============================================================================


@syndicate.command(name='clean')
@timeit
@click.option('--deploy_name', nargs=1, callback=check_required_param)
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--clean_only_types', multiple=True)
@click.option('--clean_only_resources', multiple=True)
@click.option('--clean_only_resources_path', nargs=1, type=str)
@click.option('--excluded_resources', multiple=True)
@click.option('--excluded_resources_path', nargs=1, type=str)
@click.option('--excluded_types', multiple=True)
@click.option('--rollback', is_flag=True)
def clean(deploy_name, bundle_name, clean_only_types, clean_only_resources,
          clean_only_resources_path, excluded_resources,
          excluded_resources_path, excluded_types, rollback):
    click.echo('Command clean')
    click.echo('Deploy name: %s' % deploy_name)
    if clean_only_types:
        click.echo('Clean only types: %s' % str(clean_only_types))
    if clean_only_resources:
        click.echo('Clean only resources : %s' % clean_only_resources)
    if clean_only_resources_path:
        click.echo(
            'Clean only resources path: %s' % clean_only_resources_path)
    if excluded_resources:
        click.echo('Excluded resources: %s' % str(excluded_resources))
    if excluded_resources_path:
        click.echo('Excluded resources path: %s' % excluded_resources_path)
    if excluded_types:
        click.echo('Excluded types: %s' % str(excluded_types))
    if clean_only_resources_path and os.path.exists(
            clean_only_resources_path):
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
                                       excluded_types=excluded_types)
    else:
        remove_deployment_resources(deploy_name=deploy_name,
                                    bundle_name=bundle_name,
                                    clean_only_resources=clean_only_resources,
                                    clean_only_types=clean_only_types,
                                    excluded_resources=excluded_resources,
                                    excluded_types=excluded_types)
    click.echo('AWS resources were removed.')


# =============================================================================


@syndicate.command(name='assemble_java_mvn')
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_java_mvn(bundle_name, project_path):
    click.echo('Command compile java project path: %s' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_JAVA_8)
    click.echo('Java artifacts were prepared successfully.')


@syndicate.command(name='assemble_python')
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_python(bundle_name, project_path):
    click.echo('Command assemble python: project_path: %s ' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_PYTHON)
    click.echo('Python artifacts were prepared successfully.')


@syndicate.command(name='assemble_node')
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_node(bundle_name, project_path):
    click.echo('Command assemble node: project_path: %s ' % project_path)
    assemble_artifacts(bundle_name=bundle_name,
                       project_path=project_path,
                       runtime=RUNTIME_NODEJS)
    click.echo('NodeJS artifacts were prepared successfully.')


COMMAND_TO_BUILD_MAPPING = {
    MVN_BUILD_TOOL_NAME: assemble_java_mvn,
    PYTHON_BUILD_TOOL_NAME: assemble_python,
    NODE_BUILD_TOOL_NAME: assemble_node
}


@syndicate.command(name='build_artifacts')
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.pass_context
def build_artifacts(ctx, bundle_name):
    click.echo('Building artifacts ...')
    if CONFIG.build_projects_mapping:
        for key, values in CONFIG.build_projects_mapping.items():
            for value in values:
                func = COMMAND_TO_BUILD_MAPPING.get(key)
                if func:
                    ctx.invoke(func, bundle_name=bundle_name,
                               project_path=value)
                else:
                    click.echo('Build tool is not supported: %s' % key)
    else:
        click.echo('Projects to be built are not found')


# =============================================================================


@syndicate.command(name='package_meta')
@timeit
@click.option('--bundle_name', nargs=1, callback=verify_bundle_callback)
def package_meta(bundle_name):
    click.echo('Package meta, bundle: %s' % bundle_name)
    create_meta(bundle_name)
    click.echo('Meta was configured successfully.')


# =============================================================================


@syndicate.command(name='create_deploy_target_bucket')
@timeit
def create_deploy_target_bucket():
    click.echo('Create deploy target sdk: %s' % CONFIG.deploy_target_bucket)
    create_bundles_bucket()
    click.echo('Deploy target bucket was created successfully')


@syndicate.command(name='upload_bundle')
@timeit
@click.option('--bundle_name', nargs=1, callback=verify_meta_bundle_callback)
@click.option('--force', is_flag=True)
def upload_bundle(bundle_name, force=False):
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
@timeit
@click.pass_context
def copy_bundle(ctx, bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name, force_upload):
    click.echo('Copy bundle: %s' % bundle_name)
    click.echo('Bundle name: %s' % bundle_name)
    click.echo('Source account id: %s' % src_account_id)
    click.echo('Source bucket region: %s' % src_bucket_region)
    click.echo('Source bucket name: %s' % src_bucket_name)
    futures = load_bundle(bundle_name, src_account_id, src_bucket_region,
                          src_bucket_name, role_name)
    handle_futures_progress_bar(futures)
    click.echo('Bundle was downloaded successfully')
    ctx.invoke(upload_bundle, bundle_name=bundle_name, force=force_upload)
    click.echo('Bundle was copied successfully')


# =============================================================================


@syndicate.command(name='build_bundle')
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--force_upload', is_flag=True, default=False)
@click.pass_context
@timeit
def build_bundle(ctx, bundle_name, force_upload):
    if if_bundle_exist(bundle_name=bundle_name) and not force_upload:
        click.echo('Bundle name \'{0}\' already exists '
                   'in deploy bucket. Please use another bundle '
                   'name or delete the bundle'.format(bundle_name))
        return
    ctx.invoke(build_artifacts, bundle_name=bundle_name)
    ctx.invoke(package_meta, bundle_name=bundle_name)
    ctx.invoke(upload_bundle, bundle_name=bundle_name, force=force_upload)


# =============================================================================


@syndicate.command(name='deploy')
@click.option('--deploy_name', nargs=1, callback=check_required_param)
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--deploy_only_types', multiple=True)
@click.option('--deploy_only_resources', multiple=True)
@click.option('--deploy_only_resources_path', nargs=1)
@click.option('--excluded_resources', multiple=True)
@click.option('--excluded_resources_path', nargs=1)
@click.option('--excluded_types', multiple=True)
@click.option('--continue_deploy', is_flag=True)
@click.option('--replace_output', nargs=1, is_flag=True, default=False)
@check_deploy_name_for_duplicates
@timeit
def deploy(deploy_name, bundle_name, deploy_only_types, deploy_only_resources,
           deploy_only_resources_path, excluded_resources,
           excluded_resources_path, excluded_types, continue_deploy,
           replace_output):
    click.echo('Command deploy backend')
    click.echo('Deploy name: %s' % deploy_name)
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


# =============================================================================

@syndicate.command(name='update')
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--deploy_name', nargs=1, callback=check_required_param)
@click.option('--update_only_types', multiple=True)
@click.option('--update_only_resources', multiple=True)
@click.option('--update_only_resources_path', nargs=1)
@click.option('--replace_output', nargs=1, is_flag=True, default=False)
@check_deploy_name_for_duplicates
@timeit
def update(bundle_name, deploy_name, replace_output,
           update_only_resources,
           update_only_resources_path,
           update_only_types=[]):
    """
    Updates infrastructure from the provided bundle.
    :param bundle_name: name of the bundle to get updated meta
    :param deploy_name: name of the deploy
    :param update_only_resources: list of resources names to updated
    :param update_only_resources_path: path to a json file with list of
        resources names to update
    :param update_only_types: optional. List of a resources types to update.
    :param replace_output: flag. If True, existing output file will be replaced
    :return:
    """
    click.echo('Bundle name: {}'.format(bundle_name))
    if update_only_types:
        click.echo('Types to update: {}'.format(list(update_only_types)))
    if update_only_resources:
        click.echo('Resources to update: {}'.format(list(update_only_types)))
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
        return 'Update of resources has been successfully completed'
    return 'Something went wrong during resources update'
