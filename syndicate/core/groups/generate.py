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

from syndicate.core.generators.project import (generate_project_structure,
                                               PROJECT_PROCESSORS)
from syndicate.core.generators.lambda_function import (generate_lambda_function)
from syndicate.core.helper import (check_required_param, timeit, OrderedGroup)

GENERATE_GROUP_NAME = 'generate'


@click.group(name=GENERATE_GROUP_NAME, cls=OrderedGroup, chain=True)
def generate():
    """Manages auto-generating"""


@generate.command(name='project')
@click.option('--project_name', nargs=1, callback=check_required_param,
              help='* The project name')
@click.option('--lang', nargs=1, callback=check_required_param,
              help='* The name of programming language that will '
                   'be used in the project',
              type=click.Choice(PROJECT_PROCESSORS))
@click.option('--project_path', nargs=1,
              help='The path where project structure will be created')
@click.pass_context
@timeit
def project(ctx, project_name, lang, project_path):
    """
    Generates project with all the necessary components and in a right
    folders/files hierarchy to start developing in a min.
    :param ctx:
    :param project_name: the project name
    :param lang: name of programming language that will be used in the project
    :param project_path: the path where project structure will be created
    :return:
    """
    click.echo('Project name: {}'.format(project_name))
    click.echo('Language: {}'.format(lang))

    proj_path = pathlib.Path().absolute() if not project_path else project_path
    if not os.access(proj_path, os.X_OK | os.W_OK):
        return ('Incorrect permissions for the provided path {}'.format(
            proj_path))
    click.echo('Project path: {}'.format(proj_path))
    generate_project_structure(project_name=project_name,
                               project_path=proj_path,
                               project_language=lang)


@generate.command(name='lambda')
@click.option('--project_name', nargs=1, callback=check_required_param,
              help='* The project name')
@click.option('--lang', nargs=1, callback=check_required_param,
              help='* The name of programming language that will '
                   'be used in the project',
              type=click.Choice(PROJECT_PROCESSORS))
@click.option('--project_path', nargs=1,
              help='The path where project structure will be created. '
                   '(If not specified - will be used current directory)')
@click.option('--lambda_name', nargs=1, multiple=True, type=str,
              callback=check_required_param,
              help='(multiple) * The lambda function name')
@click.pass_context
@timeit
def lambda_function(ctx, project_name, lang, project_path, lambda_name):
    """
    Generates required environment for lambda function
    :param ctx:
    :param project_name: the project name
    :param lang: name of programming language that will be used in the project
    :param project_path: the path where project structure will be created
    :param lambda_name: the lambda function name (multiple)
    :return:
    """
    proj_path = pathlib.Path().absolute() if not project_path else project_path
    if not os.access(proj_path, os.X_OK | os.W_OK):
        return ('Incorrect permissions for the provided path {}'.format(
            proj_path))

    click.echo('Project name: {}'.format(project_name))
    click.echo('Language: {}'.format(lang))
    click.echo('Project path: {}'.format(proj_path))
    click.echo('Lambda names: {}'.format(str(lambda_name)))
    generate_lambda_function(project_name=project_name,
                             project_path=proj_path,
                             project_language=lang,
                             lambda_names=lambda_name)
