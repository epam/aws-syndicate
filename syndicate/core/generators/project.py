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

import yaml

from syndicate.commons.log_helper import get_logger
from syndicate.core.generators import (_touch, _mkdir,
                                       _write_content_to_file)
from syndicate.core.generators.contents import (_get_lambda_default_policy,
                                                JAVA_ROOT_POM_TEMPLATE,
                                                SRC_MAIN_JAVA, FILE_POM)
from syndicate.core.groups import (RUNTIME_JAVA, RUNTIME_NODEJS,
                                   RUNTIME_PYTHON)
from syndicate.core.project_state import PROJECT_STATE_FILE, ProjectState

_LOG = get_logger('syndicate.core.generators.project')

SLASH_SYMBOL = '/'
FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'
FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'


def generate_project_state_file(project_name, project_path):
    project_state = dict(name=project_name)
    with open(os.path.join(project_path, PROJECT_STATE_FILE),
              'w') as state_file:
        yaml.dump(project_state, state_file)


def generate_project_structure(project_name, project_path):
    try:
        if not os.path.exists(project_path):
            raise AssertionError(
                'Path "{}" you have provided does not exist'.format(
                    project_path))

        full_project_path = project_path + SLASH_SYMBOL + project_name if (
                project_path[
                    -1] != SLASH_SYMBOL) else project_path + project_name

        _mkdir(path=full_project_path,
               fault_message='Folder {} already exists. \nOverride the '
                             'project? [y/n]: '.format(full_project_path))

        _touch(full_project_path + FILE_README)
        default_lambda_policy = _get_lambda_default_policy()
        _write_content_to_file(full_project_path + FILE_DEPLOYMENT_RESOURCES,
                               default_lambda_policy)
        _mkdir(path=os.path.join(full_project_path, 'src'), exist_ok=True)
        ProjectState.generate(project_name=project_name,
                              project_path=full_project_path)

        _LOG.info('Project {} folder has been successfully created.'.format(
            project_name))
    except Exception as e:
        _LOG.error(str(e))


def _generate_python_project_hierarchy(full_project_path, project_name=None):
    _mkdir(full_project_path + FOLDER_LAMBDAS, exist_ok=True)


def _generate_java_project_hierarchy(project_name, full_project_path):
    _touch(full_project_path + FILE_POM)
    pom_content = JAVA_ROOT_POM_TEMPLATE.replace('{project_name}',
                                                 project_name)
    _write_content_to_file(full_project_path + FILE_POM,
                           pom_content)
    _mkdir(full_project_path + SRC_MAIN_JAVA)


def _generate_nodejs_project_hierarchy(full_project_path, project_name=None):
    _mkdir(full_project_path + FOLDER_LAMBDAS, exist_ok=True)
    _mkdir(full_project_path + FOLDER_COMMONS, exist_ok=True)


PROJECT_PROCESSORS = {
    RUNTIME_JAVA: _generate_java_project_hierarchy,
    RUNTIME_NODEJS: _generate_nodejs_project_hierarchy,
    RUNTIME_PYTHON: _generate_python_project_hierarchy,
}
