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

from syndicate.commons.log_helper import get_logger
from syndicate.core.generators import (_touch,
                                       _mkdir, _write_content_to_file,
                                       FILE_LAMBDA_HANDLER_PYTHON,
                                       FILE_LAMBDA_HANDLER_NODEJS,
                                       _read_content_from_file)
from syndicate.core.generators.contents import (
    NODEJS_LAMBDA_HANDLER_TEMPLATE,
    PYTHON_LAMBDA_HANDLER_TEMPLATE,
    _generate_python_node_lambda_config,
    _generate_lambda_role_config, _generate_nodejs_node_lambda_config,
    CANCEL_MESSAGE, _generate_package_nodejs_lambda,
    _generate_package_lock_nodejs_lambda, JAVA_LAMBDA_HANDLER_CLASS,
    SRC_MAIN_JAVA, FILE_POM)
from syndicate.core.groups import (RUNTIME_JAVA, RUNTIME_NODEJS,
                                   RUNTIME_PYTHON)
from syndicate.core.project_state import ProjectState

_LOG = get_logger('syndicate.core.generators.lambda_function')

SLASH_SYMBOL = '/'

FOLDER_LAMBDAS = '/lambdas'
FOLDER_COMMONS = '/commons'

FILE_README = '/README.md'
FILE_DEPLOYMENT_RESOURCES = '/deployment_resources.json'
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

NODEJS_LAMBDA_FILES = [
    FILE_PACKAGE,
    FILE_PACKAGE_LOCK,
    FILE_LAMBDA_CONFIG,
    FILE_LAMBDA_HANDLER_NODEJS,
    FILE_DEPLOYMENT_RESOURCES
]


def generate_common_module(src_path, runtime):
    runtime_processor = COMMON_MODULE_PROCESSORS.get(runtime)
    if not runtime_processor:
        raise AssertionError(f'Unable to create a common module in {src_path}')
    runtime_processor(src_path=src_path)


def generate_lambda_function(project_path, runtime,
                             lambda_names):
    if not os.path.exists(project_path):
        _LOG.info('Project "{}" you have provided does not exist'.format(
            project_path))
        return

    if not ProjectState.check_if_project_state_exists(
            project_path=project_path):
        _LOG.info(f'Seems that the path {project_path} is not a project')
        return

    project_state = ProjectState(project_path=project_path)
    if not project_state.lambdas:
        generate_common_module(src_path=os.path.join(project_path, 'src'),
                               runtime=runtime)

    # processor = LAMBDAS_PROCESSORS.get(project_language)
    # if not processor:
    #     raise RuntimeError('Wrong project language {0}'.format(
    #         project_language))
    #
    # lambdas_path = full_project_path + FOLDER_LAMBDAS
    #
    # processor(project_name=project_name, project_path=project_path,
    #           lambda_names=lambda_names, lambdas_path=lambdas_path)
    _LOG.info(f'Lambda generating have been successfully performed.')


def _generate_python_lambdas(lambda_names, lambdas_path, project_name=None,
                             project_path=None):
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
        _write_content_to_file(
            f'{lambda_folder}/{FILE_LAMBDA_HANDLER_PYTHON}',
            PYTHON_LAMBDA_HANDLER_TEMPLATE)

        # fill deployment_resources.json
        pattern_format = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        role_def = _generate_lambda_role_config(
            pattern_format)
        _write_content_to_file(
            f'{lambda_folder}/{FILE_DEPLOYMENT_RESOURCES}',
            role_def)

        # fill lambda_config.json
        lambda_def = _generate_python_node_lambda_config(
            lambda_name,
            f'{FOLDER_LAMBDAS}/{lambda_name}')
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_CONFIG}',
                               lambda_def)
        _LOG.info(f'Lambda {lambda_name} created')


def _generate_java_lambdas(project_path, project_name, lambda_names,
                           lambdas_path):
    unified_lambda_name = _get_parts_split_by_chars(to_split=project_name,
                                                    chars=['-', '_'])
    java_package_name = unified_lambda_name.replace(' ', '')
    java_package_name = f'com.{java_package_name}'
    java_package_as_path = java_package_name.replace('.', '/')

    pom_file_path = f'{project_path}/{project_name}/{FILE_POM}'
    pom_xml_content = _read_content_from_file(pom_file_path)
    pom_xml_content = pom_xml_content.replace(
        '<!--packages to scan-->',
        f'<package>{java_package_name}</package>')
    _write_content_to_file(pom_file_path, pom_xml_content)

    full_package_path = f'{project_path}/{project_name}/{SRC_MAIN_JAVA}/' \
                        f'{java_package_as_path}'
    for lambda_name in lambda_names:
        if not os.path.exists(full_package_path):
            _mkdir(full_package_path, exist_ok=True)

        lambda_class_name = unified_lambda_name.title()
        lambda_class_name = lambda_class_name.replace(' ', '')
        java_handler_content = JAVA_LAMBDA_HANDLER_CLASS.replace(
            '{java_package_name}',
            java_package_name
        )
        java_handler_content = java_handler_content.replace(
            '{lambda_name}',
            lambda_name
        )
        java_handler_content = java_handler_content.replace(
            '{lambda_class_name}',
            lambda_class_name
        )
        lambda_role_name = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        java_handler_content = java_handler_content.replace(
            '{lambda_role_name}',
            lambda_role_name
        )
        java_handler_file_name = f'{project_path}/{project_name}/' \
                                 f'{SRC_MAIN_JAVA}/{java_package_as_path}/{lambda_class_name}.java'
        _write_content_to_file(
            java_handler_file_name,
            java_handler_content
        )

        # add role to deployment_resource.json

        dep_res_path = f'{project_path}/{project_name}' \
                       f'/{FILE_DEPLOYMENT_RESOURCES}'
        deployment_resources = json.loads(_read_content_from_file(
            dep_res_path
        ))
        deployment_resources.update(_generate_lambda_role_config(
            lambda_role_name, stringify=False))
        _write_content_to_file(dep_res_path,
                               json.dumps(deployment_resources, indent=2))

        _LOG.info(f'Lambda {lambda_name} created')


def _get_parts_split_by_chars(chars, to_split):
    result = to_split
    for char in chars:
        result = result.replace(char, ' ')
    return result


def _generate_nodejs_lambdas(lambda_names, lambdas_path, project_name=None,
                             project_path=None):
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
        _write_content_to_file(
            f'{lambda_folder}/{FILE_LAMBDA_HANDLER_NODEJS}',
            NODEJS_LAMBDA_HANDLER_TEMPLATE)

        # fill package.json
        package_def = _generate_package_nodejs_lambda(lambda_name)
        _write_content_to_file(f'{lambda_folder}/'f'{FILE_PACKAGE}',
                               package_def)

        # fill package.json
        package_lock_def = _generate_package_lock_nodejs_lambda(
            lambda_name)
        _write_content_to_file(f'{lambda_folder}/'f'{FILE_PACKAGE_LOCK}',
                               package_lock_def)

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name))
        _write_content_to_file(
            f'{lambda_folder}/{FILE_DEPLOYMENT_RESOURCES}',
            role_def)

        # fill lambda_config.json
        lambda_def = _generate_nodejs_node_lambda_config(
            lambda_name,
            f'{FOLDER_LAMBDAS}/{lambda_name}')
        _write_content_to_file(f'{lambda_folder}/{FILE_LAMBDA_CONFIG}',
                               lambda_def)
        _LOG.info(f'Lambda {lambda_name} created')


LAMBDAS_PROCESSORS = {
    RUNTIME_JAVA: _generate_java_lambdas,
    RUNTIME_NODEJS: _generate_nodejs_lambdas,
    RUNTIME_PYTHON: _generate_python_lambdas,
}


def _common_java_module(src_path):
    pass


def _common_nodejs_module(src_path):
    pass


def _common_python_module(src_path):
    common_module_path = os.path.join(src_path, 'common')
    _mkdir(path=common_module_path, exist_ok=True)
    _touch(os.path.join(common_module_path, '__init__.py'))
    abstract_lambda_path = os.path.join(common_module_path,
                                        'abstract_lambda.py')
    _touch(path=abstract_lambda_path)
    _write_content_to_file(file=abstract_lambda_path, content='#todo')
    logger_path = os.path.join(common_module_path, 'logger.py')
    _touch(path=logger_path)
    _write_content_to_file(file=logger_path, content='#todo')


COMMON_MODULE_PROCESSORS = {
    RUNTIME_JAVA: _common_java_module,
    RUNTIME_NODEJS: _common_nodejs_module,
    RUNTIME_PYTHON: _common_python_module
}
