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

from syndicate.exceptions import ArtifactAssemblingError, \
    EnvironmentError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir, \
    remove_dir, run_external_command

from syndicate.core.constants import LAMBDA_CONFIG_FILE_NAME, \
    LAMBDA_LAYER_CONFIG_FILE_NAME
from syndicate.core.helper import unpack_kwargs, build_path
from syndicate.core.resources.helper import validate_params


BIN_DIR = 'bin'
OBJ_DIR = 'obj'
X64_DIR = 'x64'
NET_8_0_DIR = 'net8.0'
DOTNET_CORE_DIR = 'dotnetcore'
STORE_DIR = 'store'

BUILD_DIR_TMP = 'dotnet_tmp'
LAMBDA_DIR = 'lambda'
LAYER_DIR = 'layer'

ARTIFACT_FILE = 'artifact.xml'

BUILD_LAMBDA_TMP_DIRS = [BIN_DIR, OBJ_DIR]
BUILD_LAYER_TMP_DIRS = [OBJ_DIR]

CHECK_DOTNET_INSTALLED_COMMAND = ['dotnet', '--info']

SYNDICATE_DIR = '.syndicate'
LOCAL_NUGET_SOURCE_NAME = 'syndicate_local_nuget_source'


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def assemble_dotnet_lambdas(
    runtime_root_dir: str, 
    bundles_dir: str,
    **kwargs
) -> None:
    from syndicate.core import CONFIG

    _check_dotnet_is_installed()
    runtime_abs_path = Path(CONFIG.project_path, runtime_root_dir)
    _LOG.info(f'Going to package lambdas starting by path {runtime_abs_path}')
    executor = ThreadPoolExecutor(max_workers=5)
    futures = []
    for root, _, files in os.walk(runtime_abs_path):
        for item in files:
            if item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
                _LOG.info(f'Going to build artifact in: {root}')
                arg = {
                    'item': item,
                    'root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(
                    _build_dotnet_lambda_layer_artifact, arg))
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            _LOG.info(future.result())

    futures = []
    for root, _, files in os.walk(runtime_abs_path):
        for item in files:
            if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                _LOG.info(f'Going to build artifact in: {root}')
                arg = {
                    'item': item,
                    'root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(
                    _build_dotnet_lambda_artifact, arg))
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            _LOG.info(future.result())

    _clean_tmp_files(bundles_dir, [BUILD_DIR_TMP])


@unpack_kwargs
def _build_dotnet_lambda_artifact(item, root, target_folder):
    _LOG.debug(f'Building artifact in {target_folder}')
    lambda_config_dict = json.load(open(build_path(root, item)))
    _LOG.debug(f'Root path: {root}')
    req_params = ['lambda_path', 'name', 'version']
    validate_params(root, lambda_config_dict, req_params)
    lambda_name = lambda_config_dict['name']
    lambda_version = lambda_config_dict['version']
    package_name = build_py_package_name(lambda_name, lambda_version)
    layers = lambda_config_dict.get('layers', [])
    output_path = build_path(target_folder, BUILD_DIR_TMP, LAMBDA_DIR,
                             lambda_name)

    command = [
        'dotnet', 'publish', root,
        '-p:GenerateRuntimeConfigurationFiles=true',
        '--configuration', 'Release',
        '--framework', 'net8.0',
        '--runtime', 'linux-x64',
        '--self-contained', 'False',
        '--output', output_path
    ]

    for layer_name in layers:
        layer_artifact_path = build_path(target_folder, BUILD_DIR_TMP,
                                         LAYER_DIR, layer_name,
                                         DOTNET_CORE_DIR, STORE_DIR, X64_DIR,
                                         NET_8_0_DIR, ARTIFACT_FILE)
        command.extend(['--manifest', layer_artifact_path])
        if not Path(layer_artifact_path).is_file():
            USER_LOG.warn(f'The \'{ARTIFACT_FILE}\' file for the layer '
                          f'\'{layer_name}\' is not found, it might lead to '
                          f'lambda \'{lambda_name}\' artifact generation '
                          f'failure.')

    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise ArtifactAssemblingError(
            f"An error occurred during lambda '{lambda_name}' packaging. "
            f"Details:\n{stdout or ''}\n{stderr or ''}"
        )
    _LOG.info(f'Running the command "{command}"\n{stdout or ""}'
              f'\n{stderr or ""}')

    zip_dir(output_path, build_path(target_folder, package_name))

    _clean_tmp_files(root, BUILD_LAMBDA_TMP_DIRS)


@unpack_kwargs
def _build_dotnet_lambda_layer_artifact(item, root, target_folder):
    _LOG.debug(f'Building artifact in {target_folder}')
    layer_config = json.load(open(build_path(root, item)))
    _LOG.debug(f'Root path: {root}')

    layer_name = layer_config['name']
    package_name = layer_config['deployment_package']
    custom_packages = layer_config.get('custom_packages', [])
    validate_params(root, layer_config, ['name', 'deployment_package'])

    output_path = build_path(target_folder, BUILD_DIR_TMP, LAYER_DIR,
                             layer_name, DOTNET_CORE_DIR, STORE_DIR)

    if custom_packages:
        _LOG.info(f'Processing layer \'{layer_name}\' custom packages '
                  f'\'{custom_packages}\'.')
        _process_custom_packages(root, custom_packages)

    _LOG.info(f'Packaging artifacts {package_name}')
    command = [
        'dotnet', 'store', '--skip-optimization',
        '--manifest', root,
        '--framework', 'net8.0',
        '--runtime', 'linux-x64',
        '--output', output_path
    ]

    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise ArtifactAssemblingError(
            f"An error occurred during lambda layer '{layer_name}' "
            f"packaging. Details:\n{stdout or ''}\n{stderr or ''}"
        )
    _LOG.info(f'Running the command "{command}"\n{stdout or ""}'
              f'\n{stderr or ""}')

    zip_dir(
        build_path(target_folder, BUILD_DIR_TMP, LAYER_DIR, layer_name),
        build_path(target_folder, package_name))

    _clean_tmp_files(root, BUILD_LAYER_TMP_DIRS)


def _check_dotnet_is_installed():
    try:
        exit_code, _, _ = run_external_command(CHECK_DOTNET_INSTALLED_COMMAND)
    except Exception as e:
        raise EnvironmentError(
            'It seems like the dotnet SDK is not installed. There is no '
            'ability to build a DotNet bundle. Please, make sure dotnet SDK '
            'is installed and retry to build a bundle.')


def _clean_tmp_files(location, dirs):
    for tmp_dir in dirs:
        _LOG.debug(f'Remove tmp directory {tmp_dir}')
        remove_dir(build_path(location, tmp_dir))


def _process_custom_packages(layer_dir, packages):
    if not _is_local_source_exist(LOCAL_NUGET_SOURCE_NAME):
        _LOG.info(
            'Syndicate local NuGet source does not exist, creating...')
        _create_local_nuget_source()

    for package in packages:
        _LOG.info(f'Publishing package \'{package}\' to local NuGet source '
                  f'\'{LOCAL_NUGET_SOURCE_NAME}\'...')

        package_path = build_path(layer_dir, package)
        command = [
            'dotnet', 'nuget',
            'push', package_path,
            '--source', LOCAL_NUGET_SOURCE_NAME
        ]

        exit_code, stdout, stderr = run_external_command(command)
        if exit_code != 0:
            raise EnvironmentError(
                f'An error occurred during publishing package \'{package}\' '
                f'into local NuGet source \'{LOCAL_NUGET_SOURCE_NAME}\'.'
                f'Details:\n{stdout or ""}\n{stderr or ""}'
            )
    _LOG.info(f'All custom packages successfully published to local NuGet '
              f'source \'{LOCAL_NUGET_SOURCE_NAME}\'.')


def _create_local_nuget_source():
    home_dir = str(Path.home())
    local_store = build_path(home_dir, SYNDICATE_DIR, LOCAL_NUGET_SOURCE_NAME)
    if not Path(local_store).exists():
        _LOG.info('Directory for local NuGet source does not exist, '
                  'creating...')
        Path(local_store).mkdir(parents=True)

    command = [
        'dotnet', 'nuget', 'add', 'source', local_store,
        '--name', LOCAL_NUGET_SOURCE_NAME
    ]

    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise EnvironmentError(
            f'An error occurred during local NuGet source creation.'
            f'Details:\n{stdout or ""}\n{stderr or ""}'
        )

    _LOG.info(f'Syndicate local NuGet source \'{LOCAL_NUGET_SOURCE_NAME}\' '
              f'created successfully.')


def _is_local_source_exist(source_name):
    command = ['dotnet', 'nuget', 'list', 'source', '--format', 'Short']
    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise EnvironmentError(
            f'An error occurred during an attempt to list NuGet sources.'
            f'Details:\n{stdout or ""}\n{stderr or ""}'
        )
    return True if source_name in stdout else False
