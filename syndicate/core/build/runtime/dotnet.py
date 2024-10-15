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
import sys

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
    package_name = build_py_package_name(lambda_name, lambda_version)
    artifact_path = str(Path(target_folder, package_name))
    tmp_output = build_path(target_folder, BUILD_DIR_TMP, LAMBDA_DIR, root)
    command = [
        'dotnet', 'lambda', 'package',
        '--project-location', root,
        '--output-package', artifact_path,
        '--msbuild-parameters', f'-p:output={tmp_output}'
    ]

    exit_code, stdout, stderr = run_external_command(command)
    if exit_code != 0:
        raise RuntimeError(
            f'An error occurred during lambda {lambda_name} packaging. '
            f'Details:\n{stdout}\n{stderr}'
        )
    _clean_tmp_files(root, BUILD_LAMBDA_TMP_DIRS)


def _check_dotnet_is_installed():
    try:
        exit_code, _, _ = run_external_command(CHECK_DOTNET_INSTALLED_COMMAND)
    except Exception as e:
        _LOG.debug(f'An error occurred during checking dotnet SDK '
                   f'installed\n{e}')
        USER_LOG.error(
            'It seems like the dotnet SDK is not installed. There is no '
            'ability to build a DotNet bundle. Please, make sure dotnet SDK '
            'is installed and retry to build a bundle.')
        sys.exit(1)


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
