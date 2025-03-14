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
from pathlib import Path

from syndicate.exceptions import InvalidValueError
from syndicate.commons.log_helper import get_logger
from syndicate.core import ProjectState
from syndicate.core.generators import (_touch, _mkdir,
                                       _write_content_to_file)
from syndicate.core.generators.contents import (_get_lambda_default_policy,
                                                JAVA_ROOT_POM_TEMPLATE,
                                                SRC_MAIN_JAVA, FILE_POM,
                                                CHANGELOG_TEMPLATE,
                                                GITIGNORE_CONTENT,
                                                README_TEMPLATE)
from syndicate.core.groups import (RUNTIME_JAVA, RUNTIME_NODEJS,
                                   RUNTIME_PYTHON, RUNTIME_DOTNET)

_LOG = get_logger(__name__)

SLASH_SYMBOL = '/'
FOLDER_LAMBDAS = 'lambdas'
FOLDER_COMMONS = 'commons'
FILE_README = 'README.md'
FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
FILE_CHANGELOG = 'CHANGELOG.md'
FILE_GITIGNORE = '.gitignore'


def generate_project_structure(project_name, project_path):
    try:
        if not os.path.exists(project_path):
            raise InvalidValueError(
                f"Path '{project_path}' you have provided does not exist"
            )

        full_project_path = os.path.join(project_path, project_name) \
            if (project_path[-1] != SLASH_SYMBOL) \
            else project_path + project_name

        _mkdir(path=full_project_path,
               fault_message='Folder {} already exists. \nOverride the '
                             'project? [y/n]: '.format(full_project_path))

        path_to_readme = os.path.join(full_project_path, FILE_README)
        _touch(path_to_readme)
        readme_template = README_TEMPLATE.replace('project_name', project_name)
        _write_content_to_file(file=path_to_readme,
                               content=readme_template)

        default_lambda_policy = _get_lambda_default_policy()
        _write_content_to_file(file=os.path.join(full_project_path,
                                                 FILE_DEPLOYMENT_RESOURCES),
                               content=default_lambda_policy)
        ProjectState.generate(project_name=project_name,
                              project_path=full_project_path)

        _write_content_to_file(os.path.join(full_project_path, FILE_CHANGELOG),
                               CHANGELOG_TEMPLATE)
        _write_content_to_file(os.path.join(full_project_path, FILE_GITIGNORE),
                               GITIGNORE_CONTENT)
        _LOG.info('Project {} folder has been successfully created.'.format(
            project_name))
    except Exception as e:
        _LOG.exception(str(e))


def _generate_python_project_hierarchy(full_project_path, project_name=None):
    _mkdir(os.path.join(full_project_path, FOLDER_LAMBDAS), exist_ok=True)


def _generate_java_project_hierarchy(project_name, full_project_path):
    pom_path = os.path.join(full_project_path, FILE_POM)
    if not os.path.exists(pom_path):
        _LOG.info(f"Generating pom inside {full_project_path}")
        _touch(path=pom_path)
        pom_content = JAVA_ROOT_POM_TEMPLATE.replace('{project_name}',
                                                     project_name)
        _write_content_to_file(file=pom_path, content=pom_content)
        _LOG.info(f"Pom file was generated by path: {pom_path}")
    else:
        _LOG.info(f"Pom file inside {full_project_path} already exists")
    _mkdir(Path(full_project_path, SRC_MAIN_JAVA), exist_ok=True)


def _generate_nodejs_project_hierarchy(full_project_path, project_name=None):
    _mkdir(os.path.join(full_project_path, FOLDER_LAMBDAS), exist_ok=True)
    _mkdir(os.path.join(full_project_path, FOLDER_COMMONS), exist_ok=True)


def _generate_dotnet_project_hierarchy(full_project_path, project_name=None):
    _mkdir(os.path.join(full_project_path, FOLDER_LAMBDAS), exist_ok=True)


PROJECT_PROCESSORS = {
    RUNTIME_JAVA: _generate_java_project_hierarchy,
    RUNTIME_NODEJS: _generate_nodejs_project_hierarchy,
    RUNTIME_PYTHON: _generate_python_project_hierarchy,
    RUNTIME_DOTNET: _generate_dotnet_project_hierarchy
}
