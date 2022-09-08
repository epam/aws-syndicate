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
from pathlib import Path

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core import ProjectState
from syndicate.core.project_state.project_state import BUILD_MAPPINGS
from syndicate.core.generators import (_touch,
                                       _mkdir, _write_content_to_file,
                                       FILE_LAMBDA_HANDLER_PYTHON,
                                       FILE_LAMBDA_HANDLER_NODEJS,
                                       _read_content_from_file)
from syndicate.core.generators.project import _generate_java_project_hierarchy
from syndicate.core.generators.tests import _generate_python_tests
from syndicate.core.generators.contents import (
    NODEJS_LAMBDA_HANDLER_TEMPLATE,
    _generate_python_node_lambda_config,
    _generate_lambda_role_config, _generate_nodejs_node_lambda_config,
    CANCEL_MESSAGE, _generate_package_nodejs_lambda,
    _generate_package_lock_nodejs_lambda, JAVA_LAMBDA_HANDLER_CLASS,
    SRC_MAIN_JAVA, FILE_POM, PYTHON_LAMBDA_HANDLER_TEMPLATE, INIT_CONTENT,
    ABSTRACT_LAMBDA_CONTENT, EXCEPTION_CONTENT, LOG_HELPER_CONTENT)
from syndicate.core.groups import (RUNTIME_JAVA, RUNTIME_NODEJS,
                                   RUNTIME_PYTHON)

_LOG = get_logger('syndicate.core.generators.lambda_function')
USER_LOG = get_user_logger()

FOLDER_LAMBDAS = 'lambdas'
FOLDER_COMMONS = 'commons'

FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
FILE_INIT_PYTHON = '__init__.py'
FILE_LAMBDA_CONFIG = 'lambda_config.json'
FILE_PACKAGE_LOCK = 'package-lock.json'
FILE_PACKAGE = 'package.json'

FILE_REQUIREMENTS = 'requirements.txt'
FILE_LOCAL_REQUIREMENTS = 'local_requirements.txt'

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name
POLICY_NAME_PATTERN = '{0}-policy'  # 0 - lambda_name

ABSTRACT_LAMBDA_NAME = 'abstract_lambda'

PROJECT_STATE_PARAM = 'project_state'
LAMBDAS_PATH_PARAM = 'lambdas_path'
LAMBDA_NAMES_PARAM = 'lambda_names'
PROJECT_NAME_PARAM = 'project_name'
PROJECT_PATH_PARAM = 'project_path'

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
        USER_LOG.info(f'Project "{project_path}" you '
                      f'have provided does not exist')
        return

    if not ProjectState.check_if_project_state_exists(
            project_path=project_path):
        USER_LOG.info(f'Seems that the path {project_path} is not a project')
        return
    project_state = ProjectState(project_path=project_path)
    src_path = os.path.join(project_path, BUILD_MAPPINGS[runtime])

    common_module_generator = COMMON_MODULE_PROCESSORS.get(runtime)
    if not common_module_generator:
        raise AssertionError(f'The runtime {runtime} is not currently '
                             f'supported to bootstrap the project')
    common_module_generator(src_path=src_path)
    project_state.add_project_build_mapping(runtime=runtime)

    processor = LAMBDAS_PROCESSORS.get(runtime)
    if not processor:
        raise RuntimeError(f'Wrong project runtime {runtime}')

    lambdas_path = os.path.join(src_path, FOLDER_LAMBDAS)

    processor(project_path=project_path, lambda_names=lambda_names,
              lambdas_path=lambdas_path, project_state=project_state)

    tests_generator = TESTS_MODULE_PROCESSORS.get(runtime)
    [tests_generator(project_path, name) for name in lambda_names]

    project_state.save()
    if len(lambda_names) == 1:
        USER_LOG.info(f'Lambda {lambda_names[0]} has been successfully '
                      f'added to the project.')
    else:
        generated_lambdas = ', '.join(lambda_names)
        USER_LOG.info(f'The following lambdas have been successfully '
                      f'added to the project: {generated_lambdas}')


def _generate_python_lambdas(**kwargs):
    lambdas_path = kwargs.get(LAMBDAS_PATH_PARAM)
    lambda_names = kwargs.get(LAMBDA_NAMES_PARAM)
    project_state = kwargs.get(PROJECT_STATE_PARAM)

    if not os.path.exists(lambdas_path):
        _mkdir(lambdas_path, exist_ok=True)

    init_file = os.path.join(lambdas_path, '__init__.py')
    _touch(init_file)
    _LOG.info(f'Lambdas path: {lambdas_path}')
    for lambda_name in lambda_names:
        lambda_folder = os.path.join(lambdas_path, lambda_name)

        answer = _mkdir(
            path=lambda_folder,
            fault_message=f'\nLambda {lambda_name} already exists.\nOverride '
                          f'the Lambda function? [y/n]: ')
        if not answer:
            _LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        PYTHON_LAMBDA_FILES.append(
            FILE_LAMBDA_HANDLER_PYTHON)  # add lambda handler
        for file in PYTHON_LAMBDA_FILES:
            _touch(os.path.join(lambda_folder, file))

        # fill handler.py
        lambda_class_name = __lambda_name_to_class_name(
            lambda_name=lambda_name)
        python_lambda_handler_template = PYTHON_LAMBDA_HANDLER_TEMPLATE. \
            replace('LambdaName', lambda_class_name)
        _write_content_to_file(os.path.join(
            lambda_folder, FILE_LAMBDA_HANDLER_PYTHON),
            python_lambda_handler_template)

        # fill deployment_resources.json
        pattern_format = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        role_def = _generate_lambda_role_config(pattern_format)
        _write_content_to_file(os.path.join(
            lambda_folder, FILE_DEPLOYMENT_RESOURCES), role_def)

        # fill lambda_config.json
        lambda_def = _generate_python_node_lambda_config(
            lambda_name,
            os.path.join(FOLDER_LAMBDAS, lambda_name))
        _write_content_to_file(os.path.join(lambda_folder, FILE_LAMBDA_CONFIG),
                               lambda_def)

        # fill local_dependencies.txt
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LOCAL_REQUIREMENTS),
            FOLDER_COMMONS)

        project_state.add_lambda(lambda_name=lambda_name, runtime='python')

        _LOG.info(f'Lambda {lambda_name} created')


def __lambda_name_to_class_name(lambda_name):
    class_name = lambda_name.split('-')
    if len(class_name) == 1:
        class_name = lambda_name.split('_')
    return ''.join([_.capitalize() for _ in class_name])


def _generate_java_lambdas(**kwargs):
    project_path = kwargs.get(PROJECT_PATH_PARAM)
    project_state = kwargs.get(PROJECT_STATE_PARAM)
    project_name = project_state.name
    lambda_names = kwargs.get(LAMBDA_NAMES_PARAM, [])

    _generate_java_project_hierarchy(project_name=project_name,
                                     full_project_path=project_path)

    java_package_name = _generate_java_package_name(project_name)
    java_package_as_path = java_package_name.replace('.', '/')

    pom_file_path = os.path.join(project_path, FILE_POM)
    pom_xml_content = _read_content_from_file(pom_file_path)
    pom_xml_content = pom_xml_content.replace(
        '<!--packages to scan-->',
        f'<package>{java_package_name}</package>')
    _write_content_to_file(pom_file_path, pom_xml_content)

    full_package_path = Path(project_path, SRC_MAIN_JAVA, java_package_as_path)
    for lambda_name in lambda_names:
        if not os.path.exists(full_package_path):
            _mkdir(full_package_path, exist_ok=True)

        lambda_class_name = _get_parts_split_by_chars(to_split=lambda_name,
                                                      chars=['-', '_']).title()
        lambda_class_name = lambda_class_name.replace(' ', '')
        lambda_role_name = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        java_handler_content = \
            (JAVA_LAMBDA_HANDLER_CLASS
             .replace('{java_package_name}', java_package_name)
             .replace('{lambda_name}', lambda_name)
             .replace('{lambda_class_name}', lambda_class_name)
             .replace('{lambda_role_name}', lambda_role_name))

        java_handler_file_name = os.path.join(
            project_path, SRC_MAIN_JAVA, java_package_as_path,
            f'{lambda_class_name}.java')
        _write_content_to_file(
            java_handler_file_name,
            java_handler_content
        )

        # add role to deployment_resource.json

        dep_res_path = os.path.join(project_path,
                                    FILE_DEPLOYMENT_RESOURCES)
        deployment_resources = json.loads(_read_content_from_file(
            dep_res_path
        ))
        deployment_resources.update(_generate_lambda_role_config(
            lambda_role_name, stringify=False))
        _write_content_to_file(dep_res_path,
                               json.dumps(deployment_resources, indent=2))

        project_state.add_lambda(lambda_name=lambda_name, runtime=RUNTIME_JAVA)
        _LOG.info(f'Lambda {lambda_name} created')


def _generate_java_package_name(project_name):
    unified_package_name = _get_parts_split_by_chars(to_split=project_name,
                                                     chars=['-', '_'])
    java_package_name = unified_package_name.replace(' ', '')
    java_package_name = f'com.{java_package_name}'
    return java_package_name


def _get_parts_split_by_chars(chars, to_split):
    result = to_split
    for char in chars:
        result = result.replace(char, ' ')
    return result


def _generate_nodejs_lambdas(**kwargs):
    lambdas_path = kwargs.get(LAMBDAS_PATH_PARAM)
    lambda_names = kwargs.get(LAMBDA_NAMES_PARAM, [])
    project_state = kwargs.get(PROJECT_STATE_PARAM)

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
            _touch(Path(lambda_folder, file))

        # fill index.js
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_HANDLER_NODEJS),
            NODEJS_LAMBDA_HANDLER_TEMPLATE)

        # fill package.json
        package_def = _generate_package_nodejs_lambda(lambda_name)
        _write_content_to_file(os.path.join(lambda_folder, FILE_PACKAGE),
                               package_def)

        # fill package.json
        package_lock_def = _generate_package_lock_nodejs_lambda(
            lambda_name)
        _write_content_to_file(os.path.join(lambda_folder, FILE_PACKAGE_LOCK),
                               package_lock_def)

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name))
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_DEPLOYMENT_RESOURCES),
            role_def)

        # fill lambda_config.json
        lambda_def = _generate_nodejs_node_lambda_config(
            lambda_name,
            os.path.join(FOLDER_LAMBDAS, lambda_name))
        _write_content_to_file(os.path.join(lambda_folder, FILE_LAMBDA_CONFIG),
                               lambda_def)
        project_state.add_lambda(lambda_name=lambda_name, runtime=RUNTIME_NODEJS)
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
    common_module_path = os.path.join(src_path, FOLDER_COMMONS)
    _mkdir(path=common_module_path, exist_ok=True)

    init_path = os.path.join(common_module_path, '__init__.py')
    _touch(init_path)
    _write_content_to_file(file=init_path, content=INIT_CONTENT)

    abstract_lambda_path = os.path.join(common_module_path,
                                        'abstract_lambda.py')
    _touch(path=abstract_lambda_path)
    _write_content_to_file(file=abstract_lambda_path,
                           content=ABSTRACT_LAMBDA_CONTENT)

    logger_path = os.path.join(common_module_path, 'log_helper.py')
    _touch(path=logger_path)
    _write_content_to_file(file=logger_path, content=LOG_HELPER_CONTENT)

    exception_path = os.path.join(common_module_path, 'exception.py')
    _touch(path=exception_path)
    _write_content_to_file(file=exception_path, content=EXCEPTION_CONTENT)


def resolve_lambda_path(project: Path, runtime: str, source: str) -> Path:
    _lambda = ''
    if runtime == RUNTIME_JAVA:
        _lambda = _generate_java_package_name(project.name).replace('.', '/')
    elif runtime in LAMBDAS_PROCESSORS:
        _lambda = FOLDER_LAMBDAS
    return project/Path(source, _lambda)


COMMON_MODULE_PROCESSORS = {
    RUNTIME_JAVA: _common_java_module,
    RUNTIME_NODEJS: _common_nodejs_module,
    RUNTIME_PYTHON: _common_python_module
}

TESTS_MODULE_PROCESSORS = {
    RUNTIME_JAVA: lambda project_path, lambda_name: None,
    RUNTIME_NODEJS: lambda project_path, lambda_name: None,
    RUNTIME_PYTHON: _generate_python_tests,
}
