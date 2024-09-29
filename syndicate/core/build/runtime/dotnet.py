"""
    Copyright 2024 EPAM Systems, Inc.

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
import concurrent
import json
import os

from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir, \
    remove_dir, run_external_command

from syndicate.core.constants import LAMBDA_CONFIG_FILE_NAME, \
    LAMBDA_LAYER_CONFIG_FILE_NAME
from syndicate.core.helper import unpack_kwargs, build_path, without_zip_ext, \
    zip_ext
from syndicate.core.resources.helper import validate_params


BIN_DIR = 'bin'
OBJ_DIR = 'obj'
STORE_DIR = 'store'
X64_DIR = 'x64'
NET_8_0_DIR = 'net8.0'

BUILD_DIR_TMP = 'dotnet_tmp'
LAMBDA_DIR = 'lambda'
LAYER_DIR = 'layer'

ARTIFACT_FILE = 'artifact.xml'

BUILD_LAMBDA_TMP_DIRS = [BIN_DIR, OBJ_DIR]
BUILD_LAYER_TMP_DIRS = [OBJ_DIR]

CHECK_DOTNET_INSTALLED_COMMAND = ['dotnet', '--info']

CHECK_AWS_TOOLS_INSTALLED_COMMAND = ['dotnet', 'lambda', 'help']
INSTALL_AWS_TOOLS_COMMAND = [
    'dotnet', 'tool', 'install', '-g', 'Amazon.Lambda.Tools']

_LOG = get_logger('dotnet_runtime_assembler')
USER_LOG = get_user_logger()


def assemble_dotnet_lambdas(project_path, bundles_dir):
    from syndicate.core import CONFIG
    project_abs_path = Path(CONFIG.project_path, project_path)
    _LOG.info(f'Going to package lambdas starting by path {project_abs_path}')
    executor = ThreadPoolExecutor(max_workers=5)
    futures = []
    for root, sub_dirs, files in os.walk(project_abs_path):
        for item in files:
            if item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
                _LOG.info(f'Going to build lambda layer in: {root}')
                arg = {
                    'layer_root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(build_dotnet_lambda_layer, arg))

    for future in concurrent.futures.as_completed(futures):
        _LOG.info(future.result())
    futures = []
    for root, sub_dirs, files in os.walk(project_abs_path):
        for item in files:
            if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                _LOG.info(f'Going to build artifact in: {root}')
                arg = {
                    'item': item,
                    'root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(_build_dotnet_artifact, arg))

    for future in concurrent.futures.as_completed(futures):
        _LOG.info(future.result())

    _clean_tmp_files(bundles_dir, [BUILD_DIR_TMP])


@unpack_kwargs
def _build_dotnet_artifact(item, root, target_folder):
    _check_dotnet_is_installed()
    _check_amazon_lambda_tools_is_installed()
    _LOG.debug(f'Building artifact in {target_folder}')
    lambda_config_dict = json.load(open(build_path(root, item)))
    _LOG.debug(f'Root path: {root}')
    req_params = ['lambda_path', 'name', 'version']
    validate_params(root, lambda_config_dict, req_params)
    lambda_name = lambda_config_dict['name']
    lambda_version = lambda_config_dict['version']
    lambda_layers = lambda_config_dict.get('layers', [])
    package_name = build_py_package_name(lambda_name, lambda_version)
    artifact_path = str(Path(target_folder, package_name))
    tmp_output = build_path(target_folder, BUILD_DIR_TMP, LAMBDA_DIR, root)
    command = [
        'dotnet', 'lambda', 'package',
        '--project-location', root,
        '--output-package', artifact_path,
        '--msbuild-parameters', f'-p:output={tmp_output}'
    ]

    if lambda_layers:
        if len(lambda_layers) > 1:
            raise AssertionError(
                f'Currently lambdas with runtime dotnet support linking with '
                f'one layer only! Lambda with name {lambda_name} has '
                f'{len(lambda_layers)} layers linked.'
            )

        layer_name = lambda_layers[0]
        layer_package_store = build_path(
            target_folder, BUILD_DIR_TMP, LAYER_DIR,
            layer_name, STORE_DIR)
        command.append(f'-p:manifest={layer_package_store}')

    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise RuntimeError(
            f'An error occurred during lambda {lambda_name} packaging. '
            f'Details:\n{stdout}\n{stderr}'
        )
    _clean_tmp_files(root, BUILD_LAMBDA_TMP_DIRS)


@unpack_kwargs
def build_dotnet_lambda_layer(layer_root: str, target_folder: str):
    with open(Path(layer_root, LAMBDA_LAYER_CONFIG_FILE_NAME), 'r') as file:
        layer_config = json.load(file)

    layer_name = layer_config['name']
    validate_params(layer_root, layer_config, ['name', 'deployment_package'])
    package_name = zip_ext(layer_config['deployment_package'])
    store_output_path = build_path(target_folder, BUILD_DIR_TMP,
                                   LAYER_DIR, layer_name, STORE_DIR)
    _LOG.info(f'Packaging artifacts {package_name}')
    _create_runtime_package_store(layer_name, layer_root, store_output_path)
    zip_dir(build_path(store_output_path, X64_DIR, NET_8_0_DIR),
            build_path(target_folder, package_name))
    _clean_tmp_files(layer_root, BUILD_LAYER_TMP_DIRS)


def _create_runtime_package_store(layer_name: str, layer_root: str,
                                  output_path: str):
    create_store_command = [
        'dotnet', 'store', '--skip-optimization',
        '--manifest', f'{layer_root}/packages.csproj',
        '--framework', 'net8.0',
        '--runtime', 'linux-x64',
        '--output', output_path
    ]

    exit_code, stdout, stderr = run_external_command(create_store_command)
    if exit_code != 0:
        raise RuntimeError(
            f'An error occurred during lambda layer {layer_name} packaging. '
            f'Details:\n{stdout}\n{stderr}'
        )


def _check_dotnet_is_installed():
    exit_code, _, _ = run_external_command(CHECK_DOTNET_INSTALLED_COMMAND)
    if exit_code != 0:
        raise AssertionError(
            'dotnet SDK is not installed. There is no ability to build '
            'DotNet bundle. Please, install dotnet SDK and retry to build a '
            'bundle.')


def _check_amazon_lambda_tools_is_installed():
    exit_code, _, _ = run_external_command(CHECK_AWS_TOOLS_INSTALLED_COMMAND)
    if exit_code != 0:
        USER_LOG.info('Amazon Lambda Tools is not installed. Installing...')
        exit_code, stdout, stderr = run_external_command(
            INSTALL_AWS_TOOLS_COMMAND)
        if exit_code != 0:
            raise AssertionError(
                'An error occurred during Amazon Lambda Tools installation. '
                f'Details:\n{stdout}\n{stderr}')


def _clean_tmp_files(location, dirs):
    for tmp_dir in dirs:
        _LOG.debug(f'Remove tmp directory {tmp_dir}')
        remove_dir(build_path(location, tmp_dir))
