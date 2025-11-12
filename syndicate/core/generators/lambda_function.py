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

from syndicate.exceptions import InvalidValueError
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
    SRC_MAIN_JAVA, PYTHON_LAMBDA_HANDLER_TEMPLATE, INIT_CONTENT,
    ABSTRACT_LAMBDA_CONTENT, EXCEPTION_CONTENT, LOG_HELPER_CONTENT,
    _generate_python_node_layer_config, REQUIREMENTS_FILE_CONTENT,
    LOCAL_REQUIREMENTS_FILE_CONTENT, _generate_node_layer_package_file,
    _generate_node_layer_package_lock_file, JAVA_TAG_ANNOTATION_TEMPLATE,
    JAVA_TAGS_ANNOTATION_TEMPLATE, JAVA_TAGS_IMPORT,
    DOTNET_LAMBDA_HANDLER_TEMPLATE, DOTNET_LAMBDA_CSPROJ_TEMPLATE,
    _generate_dotnet_lambda_config, DOTNET_LAMBDA_LAYER_CSPROJ_TEMPLATE)
from syndicate.core.groups import (PYTHON_ROOT_DIR_PYAPP, RUNTIME_JAVA, RUNTIME_NODEJS,
                                   RUNTIME_PYTHON, RUNTIME_PYTHON_LAYER,
                                   RUNTIME_NODEJS_LAYER, RUNTIME_DOTNET,
                                   RUNTIME_DOTNET_LAYER, LAYER_SUFFIX,
                                   RUNTIME_DOTNET_LAYER, PYTHON_ROOT_DIR_SRC)
from syndicate.core.constants import DEFAULT_JSON_INDENT


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

FOLDER_LAMBDAS = 'lambdas'
FOLDER_COMMONS = 'commons'
FOLDER_LAYERS = 'layers'

FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
FILE_INIT_PYTHON = '__init__.py'
FILE_LAMBDA_CONFIG = 'lambda_config.json'
FILE_PACKAGE_LOCK = 'package-lock.json'
FILE_PACKAGE = 'package.json'
FILE_LAYER_CONFIG = 'lambda_layer_config.json'

FILE_REQUIREMENTS = 'requirements.txt'
FILE_LOCAL_REQUIREMENTS = 'local_requirements.txt'

FILE_DOTNET_FUNCTION = 'Function.cs'
FILE_DOTNET_FUNCTION_CONFIG = 'Function.csproj'
FILE_DOTNET_LAYER_PACKAGES = 'packages.csproj'


LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name
POLICY_NAME_PATTERN = '{0}-policy'  # 0 - lambda_name

ABSTRACT_LAMBDA_NAME = 'abstract_lambda'

PROJECT_PATH_PARAM = 'project_path'
RUNTIME_PARAM = 'runtime'

PYTHON_LAMBDA_FILES = [
    FILE_INIT_PYTHON, FILE_LOCAL_REQUIREMENTS,
    FILE_REQUIREMENTS,
    FILE_DEPLOYMENT_RESOURCES,  # content
    FILE_LAMBDA_CONFIG  # content
]  # + handler content

PYTHON_LAYER_FILES = [
    FILE_LOCAL_REQUIREMENTS,
    FILE_REQUIREMENTS,
    FILE_LAYER_CONFIG
]

NODEJS_LAMBDA_FILES = [
    FILE_PACKAGE,
    FILE_PACKAGE_LOCK,
    FILE_LAMBDA_CONFIG,
    FILE_LAMBDA_HANDLER_NODEJS,
    FILE_DEPLOYMENT_RESOURCES
]

NODEJS_LAYER_FILES = [
    FILE_PACKAGE,
    FILE_PACKAGE_LOCK,
    FILE_LAYER_CONFIG
]

DOTNET_LAMBDA_FILES = [
    FILE_DOTNET_FUNCTION,
    FILE_DOTNET_FUNCTION_CONFIG,
    FILE_LAMBDA_CONFIG,
    FILE_DEPLOYMENT_RESOURCES
]

DOTNET_LAYER_FILES = [
    FILE_LAYER_CONFIG,
    FILE_DOTNET_LAYER_PACKAGES
]


def generate_common_module(runtime_abs_path, runtime):
    runtime_processor = COMMON_MODULE_PROCESSORS.get(runtime)
    if not runtime_processor:
        raise InvalidValueError(
            f"Runtime '{runtime}' is not supported. "
            f"Currently available runtimes: '{list(COMMON_MODULE_PROCESSORS)}'"
        )
    runtime_processor(runtime_abs_path=runtime_abs_path)


def generate_lambda_function(
    project_path:str, 
    runtime: str, 
    lambda_names: list[str], 
    tags: dict[str, str],
) -> None:
    from syndicate.core import PROJECT_STATE

    if not os.path.exists(project_path):
        USER_LOG.info(
            f'Project "{project_path}" you '
            f'have provided does not exist',
        )
        return

    runtime_abs_path = os.path.join(project_path, BUILD_MAPPINGS[runtime])

    common_module_generator = COMMON_MODULE_PROCESSORS.get(runtime)
    if not common_module_generator:
        raise InvalidValueError(
            f"The runtime '{runtime}' is not currently supported to bootstrap "
            f"the project"
        )
    common_module_generator(runtime_abs_path=runtime_abs_path)

    PROJECT_STATE.add_project_build_mapping(runtime=runtime)

    processor = LAMBDAS_PROCESSORS.get(runtime)
    if not processor:
        raise InvalidValueError(f"Wrong project runtime '{runtime}'")

    lambdas_path = os.path.join(runtime_abs_path, FOLDER_LAMBDAS)

    generated_lambdas = processor(
        project_path=project_path, lambda_names=lambda_names,
        lambdas_path=lambdas_path, project_state=PROJECT_STATE,
        tags=tags, runtime_abs_path=runtime_abs_path,
    )

    tests_generator = TESTS_MODULE_PROCESSORS.get(runtime)
    for lambda_name in lambda_names:
        tests_generator(
            runtime_abs_path=runtime_abs_path,
            lambda_name=lambda_name,
        )

    PROJECT_STATE.save()
    if len(generated_lambdas) == 1:
        USER_LOG.info(
            f'Lambda {generated_lambdas[0]} has been successfully '
            f'added to the project.',
        )
    elif len(generated_lambdas) > 1:
        generated_lambda_names = ', '.join(generated_lambdas)
        USER_LOG.info(
            f'The following lambdas have been successfully '
            f'added to the project: {generated_lambda_names}',
        )


def generate_lambda_layer(
    name: str,
    runtime: str,
    project_path: str,
    lambda_names: list[str] | None = None,
) -> None:
    from syndicate.core import PROJECT_STATE

    if not os.path.exists(project_path):
        USER_LOG.info(
            f'Project "{project_path}" you '
            f'have provided does not exist',
        )
        return
    
    runtime_abs_path = Path(project_path, BUILD_MAPPINGS[runtime])
    # For Python, layers are located in src/lambdas/layers
    # For other runtimes, layers are located in lambdas/layers
    if runtime == RUNTIME_PYTHON:
        runtime_abs_path /= PYTHON_ROOT_DIR_SRC

    common_module_generator = COMMON_MODULE_PROCESSORS.get(
        runtime + LAYER_SUFFIX
    )
    if not common_module_generator:
        raise InvalidValueError(
            f"The layer runtime '{runtime}' is not currently supported to "
            f"bootstrap the project"
        )
    common_module_generator(runtime_abs_path=runtime_abs_path)
    PROJECT_STATE.add_project_build_mapping(runtime=runtime)

    processor = LAYERS_PROCESSORS.get(runtime)
    if not processor:
        raise InvalidValueError(f"Wrong layer runtime '{runtime}'")

    layers_path = os.path.join(runtime_abs_path, FOLDER_LAMBDAS, FOLDER_LAYERS)

    result = processor(
        layer_name=name,
        layers_path=layers_path,
        runtime=runtime
    )

    PROJECT_STATE.save()

    if result is None:
        return

    USER_LOG.info(
        f'Layer \'{name}\' has been successfully '
        f'added to the project.'
    )

    if lambda_names:
        _LOG.debug(f'Going to link layer {name} with lambdas: {lambda_names}')
        project_lambdas = PROJECT_STATE.lambdas
        _link_layer_to_lambdas(
            lambda_names=lambda_names,
            layer_name=name,
            layer_runtime=runtime,
            existent_lambdas=project_lambdas,
            lambda_path=runtime_abs_path,
        )


def _generate_python_lambdas(
    runtime_abs_path: str,
    project_state: ProjectState,
    tags: dict[str, str],
    lambda_names: list[str],
    **kwargs,
) -> list[str]:
    generated_lambdas = []
    lambdas_path = os.path.join(
        runtime_abs_path, PYTHON_ROOT_DIR_SRC, FOLDER_LAMBDAS
    )

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
                          f'the Lambda function? [y/n]: ',
        )
        if not answer:
            USER_LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        PYTHON_LAMBDA_FILES.append(FILE_LAMBDA_HANDLER_PYTHON)
        for file in PYTHON_LAMBDA_FILES:
            _touch(os.path.join(lambda_folder, file))

        # fill handler.py
        lambda_class_name = __lambda_name_to_class_name(
            lambda_name=lambda_name
        )
        python_lambda_handler_template = PYTHON_LAMBDA_HANDLER_TEMPLATE. \
            replace('LambdaName', lambda_class_name)

        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_HANDLER_PYTHON),
            python_lambda_handler_template,
        )

        # fill deployment_resources.json
        pattern_format = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        role_def = _generate_lambda_role_config(pattern_format, tags)
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_DEPLOYMENT_RESOURCES),
            role_def,
        )

        # fill lambda_config.json
        lambda_def = _generate_python_node_lambda_config(
            lambda_name,
            os.path.join(FOLDER_LAMBDAS, lambda_name),
            tags,
        )
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_CONFIG),
            lambda_def,
        )

        # fill local_dependencies.txt
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LOCAL_REQUIREMENTS),
            FOLDER_COMMONS,
        )

        project_state.add_lambda(
            lambda_name=lambda_name,
            runtime=RUNTIME_PYTHON,
        )

        _LOG.info(f'Lambda {lambda_name} created')
        generated_lambdas.append(lambda_name)

    return generated_lambdas


def __lambda_name_to_class_name(lambda_name):
    class_name = lambda_name.split('-')
    if len(class_name) == 1:
        class_name = lambda_name.split('_')
    return ''.join([_.capitalize() for _ in class_name])


def _generate_java_lambdas(
    project_path: str,
    lambda_names: list[str],
    project_state: ProjectState,
    tags: dict[str, str],
    **kwargs,
) -> list[str]:
    from click import confirm as click_confirm
    project_name = project_state.name
    generated_lambdas = []

    java_project_path = os.path.join(project_path, BUILD_MAPPINGS[RUNTIME_JAVA])
    java_package_name = _generate_java_package_name(project_name)
    java_package_as_path = java_package_name.replace('.', '/')
    full_package_path = Path(
        java_project_path, SRC_MAIN_JAVA, java_package_as_path
    )

    _generate_java_project_hierarchy(
        project_name=project_name,
        java_package_name=java_package_name,
        java_project_path=java_project_path
    )
    
    for lambda_name in lambda_names:
        if not os.path.exists(full_package_path):
            _mkdir(full_package_path, exist_ok=True)

        lambda_class_name = _get_parts_split_by_chars(to_split=lambda_name,
                                                      chars=['-', '_']).title()
        lambda_class_name = lambda_class_name.replace(' ', '')
        lambda_role_name = LAMBDA_ROLE_NAME_PATTERN.format(lambda_name)
        lambda_tags_import, lambda_tags = _resolve_java_tags(tags)
        java_handler_content = (
            JAVA_LAMBDA_HANDLER_CLASS
            .replace('{java_package_name}', java_package_name)
            .replace('{lambda_name}', lambda_name)
            .replace('{lambda_class_name}', lambda_class_name)
            .replace('{lambda_role_name}', lambda_role_name)
            .replace('{tags_import}', lambda_tags_import)
            .replace('{tags}', lambda_tags)
        )

        java_handler_file_name = os.path.join(
            full_package_path, f'{lambda_class_name}.java'
        )
        if Path(str(java_handler_file_name)).is_file():
            if not click_confirm(
                    f'\nLambda {lambda_name} already exists.\nOverride '
                    f'the Lambda function?'):
                USER_LOG.info(CANCEL_MESSAGE.format(lambda_name))
                continue
        _write_content_to_file(
            java_handler_file_name,
            java_handler_content
        )

        # add role to deployment_resource.json

        dep_res_path = os.path.join(project_path,
                                    FILE_DEPLOYMENT_RESOURCES)
        if not Path(dep_res_path).is_file():
            _LOG.warning(
                'The project root \'deployment_resources.json\' file is '
                'absent. Creating...'
            )
            _touch(dep_res_path)
            deployment_resources = {}
        else:
            deployment_resources = json.loads(_read_content_from_file(
                dep_res_path
            ))
        deployment_resources.update(_generate_lambda_role_config(
            lambda_role_name, tags, stringify=False))
        _write_content_to_file(
            dep_res_path,
            json.dumps(deployment_resources, indent=DEFAULT_JSON_INDENT),
        )

        project_state.add_lambda(lambda_name=lambda_name, runtime=RUNTIME_JAVA)
        _LOG.info(f'Lambda {lambda_name} created')
        generated_lambdas.append(lambda_name)

    return generated_lambdas


def _generate_java_package_name(project_name):
    unified_package_name = _get_parts_split_by_chars(to_split=project_name,
                                                     chars=['-', '_'])
    java_package_name = unified_package_name.replace(' ', '')
    java_package_name = f'com.{java_package_name}'
    return java_package_name


def _resolve_java_tags(tags):
    if tags:
        tag_annotations = []
        for key, value in tags.items():
            tag_annotations.append(JAVA_TAG_ANNOTATION_TEMPLATE
                                   .replace('{key}', key)
                                   .replace('{value}', value))
        return (JAVA_TAGS_IMPORT,
                JAVA_TAGS_ANNOTATION_TEMPLATE.replace(
                    '{tags}', ',\n'.join(tag_annotations)))

    return '', ''


def _get_parts_split_by_chars(chars, to_split):
    result = to_split
    for char in chars:
        result = result.replace(char, ' ')
    return result


def _generate_nodejs_lambdas(
    lambdas_path: str,
    project_state: ProjectState,
    tags: dict[str, str],
    lambda_names: list[str],
    **kwargs,
) -> list[str]:
    generated_lambdas = []

    if not os.path.exists(lambdas_path):
        _mkdir(lambdas_path, exist_ok=True)

    for lambda_name in lambda_names:

        lambda_folder = os.path.join(lambdas_path, lambda_name)

        answer = _mkdir(
            path=lambda_folder,
            fault_message=f'\nLambda {lambda_name} already exists.\nOverride '
                          f'the Lambda function? [y/n]: '
        )
        if not answer:
            USER_LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        for file in NODEJS_LAMBDA_FILES:
            _touch(Path(lambda_folder, file))

        # fill index.js
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_HANDLER_NODEJS),
            NODEJS_LAMBDA_HANDLER_TEMPLATE,
        )

        # fill package.json
        package_def = _generate_package_nodejs_lambda(lambda_name)
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_PACKAGE),
            package_def,
        )

        # fill package.json
        package_lock_def = _generate_package_lock_nodejs_lambda(
            lambda_name,
        )   
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_PACKAGE_LOCK),
            package_lock_def,
        )

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name), 
            tags,
        )
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_DEPLOYMENT_RESOURCES),
            role_def,
        )

        # fill lambda_config.json
        lambda_def = _generate_nodejs_node_lambda_config(
            lambda_name,
            os.path.join(FOLDER_LAMBDAS, lambda_name),
            tags,
        )
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_CONFIG),
            lambda_def,
        )
        project_state.add_lambda(   
            lambda_name=lambda_name,
            runtime=RUNTIME_NODEJS,
        )
        _LOG.info(f'Lambda {lambda_name} created')
        generated_lambdas.append(lambda_name)

    return generated_lambdas


def _generate_dotnet_lambdas(
    lambdas_path: str,
    project_state: ProjectState,
    tags: dict[str, str],
    lambda_names: list[str],
    **kwargs,
) -> list[str]:
    generated_lambdas = []

    if not os.path.exists(lambdas_path):
        _mkdir(lambdas_path, exist_ok=True)

    for lambda_name in lambda_names:
        lambda_folder = os.path.join(lambdas_path, lambda_name)

        answer = _mkdir(
            path=lambda_folder,
            fault_message=f'\nLambda {lambda_name} already exists.\n'
                          f'Override the Lambda function? [y/n]: ',
        )
        if not answer:
            USER_LOG.info(CANCEL_MESSAGE.format(lambda_name))
            continue

        for file in DOTNET_LAMBDA_FILES:
            _touch(Path(lambda_folder, file))

        # fill Function.cs
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_DOTNET_FUNCTION),
            DOTNET_LAMBDA_HANDLER_TEMPLATE,
        )

        # fill Function.csproj
        _write_content_to_file(os.path.join(
            lambda_folder, FILE_DOTNET_FUNCTION_CONFIG),
             DOTNET_LAMBDA_CSPROJ_TEMPLATE,
        )

        # fill deployment_resources.json
        role_def = _generate_lambda_role_config(
            LAMBDA_ROLE_NAME_PATTERN.format(lambda_name), 
            tags,
        )
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_DEPLOYMENT_RESOURCES),
            role_def,
        )

        # fill lambda_config.json
        lambda_def = _generate_dotnet_lambda_config(
            lambda_name,
            os.path.join(FOLDER_LAMBDAS, lambda_name),
            tags,
        )
        _write_content_to_file(
            os.path.join(lambda_folder, FILE_LAMBDA_CONFIG),
            lambda_def
        )
        project_state.add_lambda(
            lambda_name=lambda_name,
            runtime=RUNTIME_DOTNET
        )
        _LOG.info(f'Lambda {lambda_name} created')
        generated_lambdas.append(lambda_name)

    return generated_lambdas


def _generate_python_layer(
    layer_name: str, 
    layers_path: str, 
    runtime: str
) -> str | None:
    layer_folder = os.path.join(layers_path, layer_name)
    answer = _mkdir(
        path=layer_folder,
        fault_message=f'\nLayer \'{layer_name}\' already exists.\n'
                      f'Override? [y/n]: ')

    if not answer:
        USER_LOG.info(f'Creation of the layer \'{layer_name}\' skipped')
        return

    for file in PYTHON_LAYER_FILES:
        _touch(Path(layer_folder, file))

    layer_config = _generate_python_node_layer_config(layer_name, runtime)
    _write_content_to_file(
        os.path.join(layer_folder, FILE_LAYER_CONFIG), 
        layer_config,
    )

    _write_content_to_file(
        os.path.join(layer_folder, FILE_REQUIREMENTS),
        REQUIREMENTS_FILE_CONTENT,
    )

    _write_content_to_file(
        os.path.join(layer_folder, FILE_LOCAL_REQUIREMENTS),
        LOCAL_REQUIREMENTS_FILE_CONTENT,
    )

    return layer_name


def _generate_nodejs_layer(
    layer_name: str, 
    layers_path: str, 
    runtime: str
) -> str | None:
    layer_folder = os.path.join(layers_path, layer_name)
    answer = _mkdir(
        path=layer_folder,
        fault_message=f'\nLayer \'{layer_name}\' already exists.\n'
                      f'Override? [y/n]: ')

    if not answer:
        USER_LOG.info(f'Creation of the layer \'{layer_name}\' skipped')
        return

    for file in NODEJS_LAYER_FILES:
        _touch(Path(layer_folder, file))

    layer_config = _generate_python_node_layer_config(layer_name, runtime)
    _write_content_to_file(
        os.path.join(layer_folder, FILE_LAYER_CONFIG),
        layer_config,
    )

    _write_content_to_file(
        os.path.join(layer_folder, FILE_PACKAGE),
        _generate_node_layer_package_file(layer_name),
    )

    _write_content_to_file(
        os.path.join(layer_folder, FILE_PACKAGE_LOCK),
        _generate_node_layer_package_lock_file(layer_name),
    )

    return layer_name


def _generate_dotnet_layer(
    layer_name: str, 
    layers_path: str, 
    runtime: str
) -> str | None:
    layer_folder = os.path.join(layers_path, layer_name)
    answer = _mkdir(
        path=layer_folder,
        fault_message=f'\nLayer \'{layer_name}\' already exists.\n'
                      f'Override? [y/n]: ')

    if not answer:
        USER_LOG.info(f'Creation of the layer \'{layer_name}\' skipped')
        return

    for file in DOTNET_LAYER_FILES:
        _touch(Path(layer_folder, file))

    layer_config = _generate_python_node_layer_config(layer_name, runtime)
    _write_content_to_file(
        os.path.join(layer_folder, FILE_LAYER_CONFIG),
        layer_config,
    )

    _write_content_to_file(
        os.path.join(layer_folder, FILE_DOTNET_LAYER_PACKAGES),
        DOTNET_LAMBDA_LAYER_CSPROJ_TEMPLATE,
    )

    return layer_name


def _link_layer_to_lambdas(
    lambda_names, layer_name, 
    layer_runtime, existent_lambdas, 
    lambda_path
) -> None:
    for lambda_name in lambda_names:
        if lambda_name not in existent_lambdas:
            USER_LOG.warning(
                f'The layer \'{layer_name}\' can\'t be linked with '
                f'lambda function \'{lambda_name}\' due to an '
                f'absence the function in the project.',
            )
            continue

        lambda_runtime = existent_lambdas[lambda_name][RUNTIME_PARAM]
        if lambda_runtime != layer_runtime:
            USER_LOG.warning(
                f'The layer \'{layer_name}\' with runtime '
                f'\'{layer_runtime}\' can\'t be linked with lambda '
                f'\'{lambda_name}\' with runtime '
                f'\'{lambda_runtime}\'',
            )
            continue

        config_file_path = Path(lambda_path, FOLDER_LAMBDAS,
                                lambda_name, FILE_LAMBDA_CONFIG)
        if not os.path.isfile(config_file_path):
            USER_LOG.warning(
                f'The layer \'{layer_name}\' can\'t be linked with '
                f'lambda function \'{lambda_name}\' due to an '
                f'absence the function config file.',
            )
            continue

        lambda_config = json.loads(_read_content_from_file(config_file_path))
        layers = lambda_config.get('layers')
        if isinstance(layers, list):
            layers.append(layer_name)
        else:
            layers = [layer_name]

        lambda_config['layers'] = list(set(layers))
        _write_content_to_file(
            config_file_path, 
            json.dumps(lambda_config),
        )
        USER_LOG.info(
            f'The layer \'{layer_name}\' was linked with '
            f'\'{lambda_name}\'',
        )


LAMBDAS_PROCESSORS = {
    RUNTIME_JAVA: _generate_java_lambdas,
    RUNTIME_NODEJS: _generate_nodejs_lambdas,
    RUNTIME_PYTHON: _generate_python_lambdas,
    RUNTIME_DOTNET: _generate_dotnet_lambdas
}

LAYERS_PROCESSORS = {
    RUNTIME_NODEJS: _generate_nodejs_layer,
    RUNTIME_PYTHON: _generate_python_layer,
    RUNTIME_DOTNET: _generate_dotnet_layer
}


def _common_java_module(runtime_abs_path: str) -> None:
    pass


def _common_nodejs_module(runtime_abs_path: str) -> None:
    pass


def _common_dotnet_module(runtime_abs_path: str) -> None:
    pass


def _common_python_module(runtime_abs_path: str) -> None:
    common_module_path = os.path.join(
        runtime_abs_path, PYTHON_ROOT_DIR_SRC, FOLDER_COMMONS
    )
    _mkdir(path=common_module_path, exist_ok=True)

    init_path = os.path.join(common_module_path, '__init__.py')
    if not os.path.exists(init_path):
        _touch(init_path)
        _write_content_to_file(file=init_path, content=INIT_CONTENT)

    abstract_lambda_path = os.path.join(common_module_path,
                                        'abstract_lambda.py')
    if not os.path.exists(abstract_lambda_path):
        _touch(path=abstract_lambda_path)
        _write_content_to_file(file=abstract_lambda_path,
                               content=ABSTRACT_LAMBDA_CONTENT)

    logger_path = os.path.join(common_module_path, 'log_helper.py')
    if not os.path.exists(logger_path):
        _touch(path=logger_path)
        _write_content_to_file(file=logger_path, content=LOG_HELPER_CONTENT)

    exception_path = os.path.join(common_module_path, 'exceptions.py')
    if not os.path.exists(exception_path):
        _touch(path=exception_path)
        _write_content_to_file(file=exception_path, content=EXCEPTION_CONTENT)


def resolve_lambda_path(
    project: Path, 
    runtime: str, 
    runtime_root_dir: str,
) -> Path:
    if runtime == RUNTIME_JAVA or runtime not in LAMBDAS_PROCESSORS:
        return project / runtime_root_dir

    if runtime == RUNTIME_PYTHON and runtime_root_dir == PYTHON_ROOT_DIR_PYAPP:
        lambda_relative_path = Path(
            runtime_root_dir, PYTHON_ROOT_DIR_SRC, FOLDER_LAMBDAS
            )
    else:
        lambda_relative_path = Path(runtime_root_dir, FOLDER_LAMBDAS)
    
    return project / lambda_relative_path


def _common_python_nodejs_dotnet_layer_module(runtime_abs_path):
    layer_path = os.path.join(runtime_abs_path, FOLDER_LAMBDAS, FOLDER_LAYERS)
    _mkdir(path=layer_path, exist_ok=True)


COMMON_MODULE_PROCESSORS = {
    RUNTIME_JAVA: _common_java_module,
    RUNTIME_NODEJS: _common_nodejs_module,
    RUNTIME_PYTHON: _common_python_module,
    RUNTIME_DOTNET: _common_dotnet_module,
    RUNTIME_PYTHON_LAYER: _common_python_nodejs_dotnet_layer_module,
    RUNTIME_NODEJS_LAYER: _common_python_nodejs_dotnet_layer_module,
    RUNTIME_DOTNET_LAYER: _common_python_nodejs_dotnet_layer_module

}

TESTS_MODULE_PROCESSORS = {
    RUNTIME_JAVA: lambda runtime_abs_path, lambda_name: None,
    RUNTIME_NODEJS: lambda runtime_abs_path, lambda_name: None,
    RUNTIME_DOTNET: lambda runtime_abs_path, lambda_name: None,
    RUNTIME_PYTHON: _generate_python_tests,
}
