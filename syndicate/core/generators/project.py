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
from syndicate.core.generators import (_touch, _mkdir,
                                       _write_content_to_file)
from syndicate.core.generators.contents import (_get_lambda_default_policy,
                                                JAVA_ROOT_POM_TEMPLATE,
                                                SRC_MAIN_JAVA, FILE_POM)
from syndicate.core.groups import (PROJECT_JAVA, PROJECT_NODEJS,
                                   PROJECT_PYTHON)

_LOG = get_logger('syndicate.core.generators.project')

SLASH_SYMBOL = '/'
FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'
FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'



def generate_project_structure(project_name, project_path, project_language):
    try:
        if not os.path.exists(project_path):
            raise AssertionError(
                'Path "{}" you have provided does not exist'.format(
                    project_path))

        processor = PROJECT_PROCESSORS.get(project_language)
        if not processor:
            raise RuntimeError('Wrong project language {0}'.format(
                project_language))

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

        processor(project_name=project_name,
                  full_project_path=full_project_path)
        _LOG.info('Project {} has been successfully created.'.format(
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
    PROJECT_JAVA: _generate_java_project_hierarchy,
    PROJECT_NODEJS: _generate_nodejs_project_hierarchy,
    PROJECT_PYTHON: _generate_python_project_hierarchy,
}
