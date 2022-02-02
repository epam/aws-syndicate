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
import click
from syndicate.core.build.bundle_processor import load_deploy_output


TAGS_GROUP_NAME = 'tags'


@click.group(name=TAGS_GROUP_NAME)
@click.pass_context
def tags(ctx):
    """Manage resources tags"""
    from syndicate.core import PROJECT_STATE, RESOURCES_PROVIDER
    if not PROJECT_STATE.latest_deploy:
        click.echo('No latest deploy')
        raise click.Abort
    deploy_name = PROJECT_STATE.latest_deploy.get('deploy_name')
    bundle_name = PROJECT_STATE.latest_deploy.get('bundle_name')
    output = load_deploy_output(bundle_name, deploy_name)
    ctx.ensure_object(dict)
    ctx.obj['output'] = output
    ctx.obj['tags_resource'] = RESOURCES_PROVIDER.tags_api()


@tags.command(name='apply')
@click.pass_context
def apply(ctx):
    """Assign tags from config to deployed resources"""
    output = ctx.obj['output']
    ctx.obj['tags_resource'].apply_tags(output)


@tags.command(name='remove')
@click.pass_context
def remove(ctx):
    """Remove tags from config from deployed resources"""
    output = ctx.obj['output']
    ctx.obj['tags_resource'].remove_tags(output)
