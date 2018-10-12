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
from syndicate.core.build.artifact_processor import (build_mvn_lambdas,
                                                     build_python_lambdas)
from syndicate.core.build.bundle_processor import (create_bundles_bucket,
                                                   load_bundle,
                                                   upload_bundle_to_s3)
from syndicate.core.build.deployment_processor import (
    create_deployment_resources,
    remove_deployment_resources, update_lambdas)
from syndicate.core.build.meta_processor import create_meta
from syndicate.core.conf.config_holder import (MVN_BUILD_TOOL_NAME,
                                               PYTHON_BUILD_TOOL_NAME)
from syndicate.core.helper import (check_required_param,
                                   create_bundle_callback,
                                   handle_futures_progress_bar,
                                   resolve_path_callback,
                                   timeit, verify_bundle_callback,
                                   verify_meta_bundle_callback)


# TODO - command descriptions


@click.group()
def syndicate():
    click.echo('Group syndicate')
    click.echo('Path to sdct.conf: ' + CONF_PATH)


# =============================================================================


@syndicate.command()
@timeit
@click.option('--deploy_name', nargs=1, callback=check_required_param)
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--clean_only_types', multiple=True)
@click.option('--clean_only_resources', multiple=True)
@click.option('--clean_only_resources_path', nargs=1, type=str)
@click.option('--excluded_resources', multiple=True)
@click.option('--excluded_resources_path', nargs=1, type=str)
@click.option('--excluded_types', multiple=True)
def clean(deploy_name, bundle_name, clean_only_types, clean_only_resources,
          clean_only_resources_path, excluded_resources,
          excluded_resources_path, excluded_types):
    click.echo('Command clean')
    click.echo('Deploy name: %s' % deploy_name)
    if clean_only_types:
        click.echo('Clean only types: %s' % str(clean_only_types))
    if clean_only_resources:
        click.echo('Clean only resources : %s' % clean_only_resources)
    if clean_only_resources_path:
        click.echo('Clean only resources path: %s' % clean_only_resources_path)
    if excluded_resources:
        click.echo('Excluded resources: %s' % str(excluded_resources))
    if excluded_resources_path:
        click.echo('Excluded resources path: %s' % excluded_resources_path)
    if excluded_types:
        click.echo('Excluded types: %s' % str(excluded_types))
    if clean_only_resources_path and os.path.exists(clean_only_resources_path):
        clean_resources_list = json.load(open(clean_only_resources_path))
        clean_only_resources = tuple(
            set(clean_only_resources + tuple(clean_resources_list)))
    if excluded_resources_path and os.path.exists(excluded_resources_path):
        excluded_resources_list = json.load(open(excluded_resources_path))
        excluded_resources = tuple(
            set(excluded_resources + tuple(excluded_resources_list)))
    remove_deployment_resources(deploy_name=deploy_name,
                                bundle_name=bundle_name,
                                clean_only_resources=clean_only_resources,
                                clean_only_types=clean_only_types,
                                excluded_resources=excluded_resources,
                                excluded_types=excluded_types)
    click.echo('AWS resources were removed.')


# =============================================================================


@syndicate.command()
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def mvn_compile_java(bundle_name, project_path):
    click.echo('Command compile java project path: %s' % project_path)
    build_mvn_lambdas(bundle_name, project_path)
    click.echo('Java artifacts were prepared successfully.')


@syndicate.command()
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--project_path', '-path', nargs=1,
              callback=resolve_path_callback)
def assemble_python(bundle_name, project_path):
    click.echo('Command assemble python: project_path: %s ' % project_path)
    build_python_lambdas(bundle_name, project_path)
    click.echo('Python artifacts were prepared successfully.')


COMMAND_TO_BUILD_MAPPING = {
    MVN_BUILD_TOOL_NAME: mvn_compile_java,
    PYTHON_BUILD_TOOL_NAME: assemble_python
}


@syndicate.command()
@timeit
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.pass_context
def build_artifacts(ctx, bundle_name):
    click.echo('Building artifacts ...')
    if CONFIG.build_projects_mapping:
        for key, values in CONFIG.build_projects_mapping.iteritems():
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


@syndicate.command()
@timeit
@click.option('--bundle_name', nargs=1, callback=verify_bundle_callback)
def package_meta(bundle_name):
    click.echo('Package meta, bundle: %s' % bundle_name)
    create_meta(bundle_name)
    click.echo('Meta was configured successfully.')


# =============================================================================


@syndicate.command()
@timeit
def create_deploy_target_bucket():
    click.echo('Create deploy target sdk: %s' % CONFIG.deploy_target_bucket)
    create_bundles_bucket()
    click.echo('Deploy target bucket was created successfully')


@syndicate.command()
@timeit
@click.option('--bundle_name', nargs=1, callback=verify_meta_bundle_callback)
def upload_bundle(bundle_name):
    click.echo('Upload bundle: %s' % bundle_name)
    futures = upload_bundle_to_s3(bundle_name)
    handle_futures_progress_bar(futures)
    click.echo('Bundle was uploaded successfully')


@syndicate.command()
@click.option('--bundle_name', nargs=1, callback=create_bundle_callback)
@click.option('--src_account_id', '-acc_id', nargs=1,
              callback=check_required_param)
@click.option('--src_bucket_region', '-r', nargs=1,
              callback=check_required_param)
@click.option('--src_bucket_name', '-bucket_name', nargs=1,
              callback=check_required_param)
@click.option('--role_name', '-role', nargs=1,
              callback=check_required_param)
@timeit
@click.pass_context
def copy_bundle(ctx, bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name):
    click.echo('Copy bundle: %s' % bundle_name)
    click.echo('Bundle name: %s' % bundle_name)
    click.echo('Source account id: %s' % src_account_id)
    click.echo('Source bucket region: %s' % src_bucket_region)
    click.echo('Source bucket name: %s' % src_bucket_name)
    futures = load_bundle(bundle_name, src_account_id, src_bucket_region,
                          src_bucket_name, role_name)
    handle_futures_progress_bar(futures)
    click.echo('Bundle was downloaded successfully')
    ctx.invoke(upload_bundle, bundle_name=bundle_name)
    click.echo('Bundle was copied successfully')


# =============================================================================


@syndicate.command()
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.pass_context
@timeit
def build_bundle(ctx, bundle_name):
    ctx.invoke(build_artifacts, bundle_name=bundle_name)
    ctx.invoke(package_meta, bundle_name=bundle_name)
    ctx.invoke(upload_bundle, bundle_name=bundle_name)


# =============================================================================


@syndicate.command()
@click.option('--deploy_name', nargs=1, callback=check_required_param)
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--deploy_only_types', multiple=True)
@click.option('--deploy_only_resources', multiple=True)
@click.option('--deploy_only_resources_path', nargs=1)
@click.option('--excluded_resources', multiple=True)
@click.option('--excluded_resources_path', nargs=1)
@click.option('--excluded_types', multiple=True)
@timeit
def deploy(deploy_name, bundle_name, deploy_only_types, deploy_only_resources,
           deploy_only_resources_path, excluded_resources,
           excluded_resources_path, excluded_types):
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
    create_deployment_resources(deploy_name, bundle_name,
                                deploy_only_resources, deploy_only_types,
                                excluded_resources, excluded_types)
    click.echo('Backend resources were deployed.')


# =============================================================================

@syndicate.command()
@click.option('--bundle_name', nargs=1, callback=check_required_param)
@click.option('--publish_only_lambdas', multiple=True)
@click.option('--publish_only_lambdas_path', nargs=1)
@click.option('--excluded_lambdas_resources', multiple=True)
@click.option('--excluded_lambdas_resources_path', nargs=1)
@timeit
def publish_lambda_version(bundle_name,
                           publish_only_lambdas, publish_only_lambdas_path,
                           excluded_lambdas_resources,
                           excluded_lambdas_resources_path):
    click.echo('Command deploy backend')
    click.echo('Bundle name: %s' % bundle_name)
    if publish_only_lambdas_path and os.path.exists(
            publish_only_lambdas_path):
        update_lambdas_list = json.load(open(publish_only_lambdas_path))
        publish_only_lambdas = tuple(
            set(publish_only_lambdas + tuple(update_lambdas_list)))
    if excluded_lambdas_resources_path and os.path.exists(
            excluded_lambdas_resources_path):
        excluded_lambdas_list = json.load(
            open(excluded_lambdas_resources_path))
        excluded_lambdas_resources = tuple(
            set(excluded_lambdas_resources + tuple(excluded_lambdas_list)))
    update_lambdas(bundle_name=bundle_name,
                   publish_only_lambdas=publish_only_lambdas,
                   excluded_lambdas_resources=excluded_lambdas_resources)
    click.echo('Lambda versions were published.')
