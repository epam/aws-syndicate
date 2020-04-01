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

from syndicate.commons.log_helper import get_logger
from syndicate.core.groups import (PROJECT_JAVA, PROJECT_NODEJS, PROJECT_PYTHON)

_LOG = get_logger('syndicate.core.project.processor')

SLASH_SYMBOL = '/'
FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'
FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'
FILE_POM = '/pom.xml'


def _touch(path):
    with open(path, 'a'):
        os.utime(path, None)


def generate_lambda_function(project_name, project_path, project_language,
                             lambda_name):
    if not os.path.exists(project_path):
        raise AssertionError(
            'Path "{}" you have provided does not exist'.format(project_path))

    processor = PROJECT_PROCESSORS.get(project_language)
    if not processor:
        raise RuntimeError('Wrong project language {0}'.format(
            project_language))

    full_project_path = project_path + SLASH_SYMBOL + project_name if (
            project_path[-1] != SLASH_SYMBOL) else project_path + project_name

    try:
        os.makedirs(full_project_path)
    except FileExistsError:
        answer = input('Folder with name {0} is already exist by path {1}. '
                       '\nOverride the project? [y/n]: '.format(
                        project_name, project_path))
        while answer not in ('y', 'n'):
            answer = input('Please enter [y/n] value: ')
            if answer == 'y':
                os.makedirs(full_project_path, exist_ok=True)
            elif answer == 'n':
                return

    os.makedirs(full_project_path + FOLDER_LAMBDAS, exist_ok=True)
    _touch(full_project_path + FILE_README)
    _touch(full_project_path + FILE_DEPLOYMENT_RESOURCES)

    processor(full_project_path)
    _LOG.info('Project {} has been successfully created.'.format(project_name))


def _generate_python_project_hierarchy(full_project_path):
    pass


def _generate_java_project_hierarchy(full_project_path):
    _touch(full_project_path + FILE_POM)


def _generate_nodejs_project_hierarchy(full_project_path):
    os.makedirs(full_project_path + FOLDER_COMMONS, exist_ok=True)


PROJECT_PROCESSORS = {
    PROJECT_JAVA: _generate_java_project_hierarchy,
    PROJECT_NODEJS: _generate_nodejs_project_hierarchy,
    PROJECT_PYTHON: _generate_python_project_hierarchy,
}
