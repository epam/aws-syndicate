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
from syndicate.core.generators import (_touch,
                                       _mkdir, _write_content_to_file)
from syndicate.core.generators.contents import (
    NODEJS_LAMBDA_HANDLER_TEMPLATE,
    PYTHON_LAMBDA_HANDLER_TEMPLATE,
    _generate_python_node_lambda_config,
    _generate_lambda_role_config)
from syndicate.core.groups import (PROJECT_JAVA, PROJECT_NODEJS,
                                   PROJECT_PYTHON)

_LOG = get_logger('syndicate.core.generators.lambda_function')

SLASH_SYMBOL = '/'

FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'
FOLDER_SRC = '/src'
FOLDER_MAIN = '/main'
FOLDER_TEST = '/test'

FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'
FILE_POM = '/pom.xml'
FILE_INIT_PYTHON = '/__init__.py'
FILE_LAMBDA_CONFIG = '/lambda_config.json'
FILE_INDEX_JS = '/index.js'
FILE_PACKAGE_LOCK = '/package-lock.json'
FILE_PACKAGE = '/package.json'

FILE_REQUIREMENTS = '/requirements.txt'
FILE_LOCAL_REQUIREMENTS = '/local_requirements.txt'

FILE_LAMBDA_HANDLER = '/handler.py'

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name
POLICY_NAME_PATTERN = '{0}-policy'  # 0 - lambda_name

PYTHON_LAMBDA_FILES = [
    FILE_INIT_PYTHON, FILE_LOCAL_REQUIREMENTS,
    FILE_REQUIREMENTS,
    FILE_DEPLOYMENT_RESOURCES,  # content
    FILE_LAMBDA_CONFIG  # content
]  # + handler content

NODEJS_LAMBDA_FILES = [FILE_PACKAGE, FILE_PACKAGE_LOCK, FILE_INDEX_JS,
                       FILE_DEPLOYMENT_RESOURCES, FILE_LAMBDA_CONFIG]


def generate_lambda_function(project_name, project_path, project_language,
                             lambda_names):
    full_project_path = project_path + SLASH_SYMBOL + project_name if (
            project_path[-1] != SLASH_SYMBOL) else project_path + project_name

    if not os.path.exists(full_project_path):
        raise AssertionError(
            'Project "{}" you have provided does not exist'.format(
                full_project_path))

    processor = LAMBDAS_PROCESSORS.get(project_language)
    if not processor:
        raise RuntimeError('Wrong project language {0}'.format(
            project_language))

    lambdas_path = full_project_path + FOLDER_LAMBDAS

    if not os.path.exists(lambdas_path):
        _mkdir(full_project_path + FOLDER_LAMBDAS, exist_ok=True)

    processor(lambda_names, lambdas_path)

    _LOG.info('Project {} has been successfully created.'.format(project_name))


def _generate_python_project_lambdas(lambda_names, lambdas_path):
    for lambda_name in lambda_names:
        print(lambdas_path)
        lambda_folder = lambdas_path + SLASH_SYMBOL + lambda_name

        _mkdir(
            path=lambda_folder,
            fault_message='Lambda {} already exists.\nOverride the '
                          'Lambda function? [y/n]: '.format(lambda_name))

        PYTHON_LAMBDA_FILES.append(FILE_LAMBDA_HANDLER)  # add lambda handler
        for file in PYTHON_LAMBDA_FILES:
            _touch(lambda_folder + file)

        # fill handler.py
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_HANDLER}',
                               PYTHON_LAMBDA_HANDLER_TEMPLATE)

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name))
        _write_content_to_file(f'{lambda_folder}/{FILE_DEPLOYMENT_RESOURCES}',
                               role_def)

        # fill lambda_config.json
        lambda_def = _generate_python_node_lambda_config(
            lambda_name,
            f'{FOLDER_LAMBDAS}/{lambda_name}')
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_CONFIG}',
                               lambda_def)


def _generate_java_project_lambdas(lambda_names, lambdas_path):
    for lambda_function in lambda_names:
        lambda_folder = lambdas_path + SLASH_SYMBOL + lambda_function
        _mkdir(lambda_folder, exist_ok=True)

        src_folder_path = lambda_folder + FOLDER_SRC
        _mkdir(src_folder_path, exist_ok=True)
        _mkdir(src_folder_path + FOLDER_MAIN, exist_ok=True)
        _mkdir(src_folder_path + FOLDER_TEST, exist_ok=True)

        _touch(lambda_folder + FILE_DEPLOYMENT_RESOURCES)
        _touch(lambda_folder + FILE_POM)


def _generate_nodejs_project_lambdas(lambda_names, lambdas_path):
    for lambda_function in lambda_names:
        lambda_folder = lambdas_path + SLASH_SYMBOL + lambda_function
        _mkdir(lambda_folder, exist_ok=True)

        for file in NODEJS_LAMBDA_FILES:
            _touch(lambda_folder + file)

        lambda_handler_path = (lambda_folder + SLASH_SYMBOL + FILE_INDEX_JS)

        with open(lambda_handler_path, 'w') as f:
            f.write(NODEJS_LAMBDA_HANDLER_TEMPLATE)


LAMBDAS_PROCESSORS = {
    PROJECT_JAVA: _generate_java_project_lambdas,
    PROJECT_NODEJS: _generate_nodejs_project_lambdas,
    PROJECT_PYTHON: _generate_python_project_lambdas,
}
