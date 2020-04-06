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
                                       _mkdir, _write_content_to_file,
                                       FILE_LAMBDA_HANDLER_PYTHON,
                                       FILE_LAMBDA_HANDLER_NODEJS)
from syndicate.core.generators.contents import (
    NODEJS_LAMBDA_HANDLER_TEMPLATE,
    PYTHON_LAMBDA_HANDLER_TEMPLATE,
    _generate_python_node_lambda_config,
    _generate_lambda_role_config, _generate_nodejs_node_lambda_config,
    CANCEL_MESSAGE, _generate_package_nodejs_lambda,
    _generate_package_lock_nodejs_lambda)
from syndicate.core.groups import (PROJECT_JAVA, PROJECT_NODEJS,
                                   PROJECT_PYTHON)

_LOG = get_logger('syndicate.core.generators.lambda_function')

SLASH_SYMBOL = '/'

FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'
FOLDER_SRC = '/src'
FOLDER_MAIN = '/main'
FOLDER_JAVA = '/java'
FOLDER_TEST = '/test'

FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'
FILE_POM = '/pom.xml'
FILE_INIT_PYTHON = '/__init__.py'
FILE_LAMBDA_CONFIG = '/lambda_config.json'
FILE_PACKAGE_LOCK = '/package-lock.json'
FILE_PACKAGE = '/package.json'

FILE_REQUIREMENTS = '/requirements.txt'
FILE_LOCAL_REQUIREMENTS = '/local_requirements.txt'

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name
POLICY_NAME_PATTERN = '{0}-policy'  # 0 - lambda_name

PYTHON_LAMBDA_FILES = [
    FILE_INIT_PYTHON, FILE_LOCAL_REQUIREMENTS,
    FILE_REQUIREMENTS,
    FILE_DEPLOYMENT_RESOURCES,  # content
    FILE_LAMBDA_CONFIG  # content
]  # + handler content

NODEJS_LAMBDA_FILES = [FILE_PACKAGE, FILE_PACKAGE_LOCK, FILE_LAMBDA_CONFIG,
                       FILE_LAMBDA_HANDLER_NODEJS, FILE_DEPLOYMENT_RESOURCES]


def generate_lambda_function(project_name, project_path, project_language,
                             lambda_names):
    full_project_path = os.path.join(project_path, project_name)

    if not os.path.exists(full_project_path):
        raise AssertionError(
            'Project "{}" you have provided does not exist'.format(
                full_project_path))

    processor = LAMBDAS_PROCESSORS.get(project_language)
    if not processor:
        raise RuntimeError('Wrong project language {0}'.format(
            project_language))

    lambdas_path = full_project_path + FOLDER_LAMBDAS

    processor(lambda_names, lambdas_path)
    _LOG.info(f'Lambda generating have been successfully performed.')


def _generate_python_lambdas(lambda_names, lambdas_path):
    if not os.path.exists(lambdas_path):
        _mkdir(lambdas_path, exist_ok=True)
    for lambda_name in lambda_names:
        print(lambdas_path)
        lambda_folder = os.path.join(lambdas_path, lambda_name)

        answer = _mkdir(
            path=lambda_folder,
            fault_message=f'\nLambda {lambda_name} already exists.\nOverride the '
            'Lambda function? [y/n]: ')
        if not answer:
            _LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        PYTHON_LAMBDA_FILES.append(
            FILE_LAMBDA_HANDLER_PYTHON)  # add lambda handler
        for file in PYTHON_LAMBDA_FILES:
            _touch(lambda_folder + file)

        # fill handler.py
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_HANDLER_PYTHON}',
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
        _LOG.info(f'Lambda {lambda_name} created')


def _generate_java_lambdas(lambda_names, lambdas_path):
    for lambda_name in lambda_names:
        lambda_folder = os.path.join(lambdas_path, lambda_name)
        _mkdir(lambda_folder)

        java_folder_path = lambda_folder + FOLDER_SRC + \
                           FOLDER_MAIN + FOLDER_JAVA
        _mkdir(java_folder_path, exist_ok=True)

        _touch(lambda_folder + FILE_DEPLOYMENT_RESOURCES)
        _touch(lambda_folder + FILE_POM)
        _LOG.info(f'Lambda {lambda_name} created')


def _generate_nodejs_lambdas(lambda_names, lambdas_path):
    if not os.path.exists(lambdas_path):
        _mkdir(lambdas_path, exist_ok=True)
    for lambda_name in lambda_names:

        lambda_folder = os.path.join(lambdas_path, lambda_name)

        answer = _mkdir(
            path=lambda_folder,
            fault_message=f'\nLambda {lambda_name} already exists.\n'
            f'Override the Lambda function? [y/n]: ')
        if not answer:
            _LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        for file in NODEJS_LAMBDA_FILES:
            _touch(lambda_folder + file)

        # fill index.js
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_HANDLER_NODEJS}',
                               NODEJS_LAMBDA_HANDLER_TEMPLATE)

        # fill package.json
        package_def = _generate_package_nodejs_lambda(lambda_name)
        _write_content_to_file(f'{lambda_folder}/'f'{FILE_PACKAGE}',
                               package_def)

        # fill package.json
        package_lock_def = _generate_package_lock_nodejs_lambda(lambda_name)
        _write_content_to_file(f'{lambda_folder}/'f'{FILE_PACKAGE_LOCK}',
                               package_lock_def)

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name))
        _write_content_to_file(f'{lambda_folder}/{FILE_DEPLOYMENT_RESOURCES}',
                               role_def)

        # fill lambda_config.json
        lambda_def = _generate_nodejs_node_lambda_config(
            lambda_name,
            f'{FOLDER_LAMBDAS}/{lambda_name}')
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_CONFIG}',
                               lambda_def)
        _LOG.info(f'Lambda {lambda_name} created')


LAMBDAS_PROCESSORS = {
    PROJECT_JAVA: _generate_java_lambdas,
    PROJECT_NODEJS: _generate_nodejs_lambdas,
    PROJECT_PYTHON: _generate_python_lambdas,
}
