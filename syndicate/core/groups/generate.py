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
import pathlib

import click

from syndicate.core.generators.lambda_function import (
    generate_lambda_function)
from syndicate.core.generators.project import (generate_project_structure,
                                               PROJECT_PROCESSORS)
from syndicate.core.helper import (check_required_param, timeit, OrderedGroup)

GENERATE_GROUP_NAME = 'generate'


@click.group(name=GENERATE_GROUP_NAME, cls=OrderedGroup, chain=True)
def generate():
    """Manages auto-generating"""


@generate.command(name='project')
@click.option('--name', nargs=1, callback=check_required_param,
              help='* The project name')
@click.option('--path', nargs=1,
              help='The path where project structure will be created')
@click.pass_context
@timeit
def project(ctx, name, path):
    """
    Generates project with all the necessary components and in a right
    folders/files hierarchy to start developing in a min.
    """
    click.echo('Project name: {}'.format(name))

    proj_path = os.getcwd() if not path else path
    if not os.access(proj_path, os.X_OK | os.W_OK):
        return ('Incorrect permissions for the provided path {}'.format(
            proj_path))
    click.echo('Project path: {}'.format(proj_path))
    generate_project_structure(project_name=name,
                               project_path=proj_path)


@generate.command(name='lambda')
@click.option('--name', nargs=1, multiple=True, type=str,
              callback=check_required_param,
              help='(multiple) * The lambda function name')
@click.option('--runtime', nargs=1, callback=check_required_param,
              help='* The name of programming language that will '
                   'be used in the project',
              type=click.Choice(PROJECT_PROCESSORS))
@click.option('--project_path', nargs=1,
              help='The path of the project to add lambda '
                   'in case it differs from $CWD')
@click.pass_context
@timeit
def lambda_function(ctx, name, runtime, project_path):
    """
    Generates required environment for lambda function
    """
    proj_path = pathlib.Path().absolute() if not project_path else project_path
    if not os.access(proj_path, os.X_OK | os.W_OK):
        return ('Incorrect permissions for the provided path {}'.format(
            proj_path))

    click.echo(f'Lambda names: {name}')
    click.echo(f'Runtime: {runtime}')
    click.echo(f'Project path: {proj_path}')
    generate_lambda_function(project_path=proj_path,
                             runtime=runtime,
                             lambda_names=name)
