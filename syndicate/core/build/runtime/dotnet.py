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
import shutil
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import build_py_package_name
from syndicate.core.constants import LAMBDA_CONFIG_FILE_NAME
from syndicate.core.helper import unpack_kwargs, build_path
from syndicate.core.resources.helper import validate_params

BIN_DIR = 'bin'
OBJ_DIR = 'obj'

BUILD_TMP_DIRS = [BIN_DIR, OBJ_DIR]

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
            # elif item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
            #     _LOG.info(f'Going to build lambda layer in `{root}`')
            #     arg = {
            #         'layer_root': root,
            #         'target_folder': bundles_dir
            #     }
            #     futures.append(executor.submit(build_node_lambda_layer, arg))
    for future in concurrent.futures.as_completed(futures):
        _LOG.info(future.result())


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

    result = subprocess.run(
        f'dotnet lambda package '
        f'--project-location {root} '
        f'--output-package {artifact_path}',
        capture_output=True, text=True)
    if result.returncode != 0:
        _LOG.info(f'\n{result.stdout}\n{result.stderr}')

    _LOG.debug(f'Going to remove lambdas\' {lambda_name} tmp directories')
    _clean_tmp_files(root, BUILD_TMP_DIRS)


def _check_dotnet_is_installed():
    result = subprocess.run('dotnet --info', capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            'dotnet SDK is not installed. There is no ability to build '
            'DotNet bundle. Please, install dotnet SDK and retry to build '
            'bundle.')


def _check_amazon_lambda_tools_is_installed():
    result = subprocess.run('dotnet lambda help', capture_output=True, text=True)
    if result.returncode != 0:
        USER_LOG.info('Amazon Lambda Tools is not installed. Installing...')
        result = subprocess.run('dotnet tool install -g Amazon.Lambda.Tools',
                                capture_output=True, text=True)
        if result.returncode != 0:
            _LOG.info(f'\n{result.stdout}\n{result.stderr}')
            raise AssertionError(
                'An error occurred during Amazon Lambda Tools installation. '
                f'Details:\n{result.stdout}\n{result.stderr}')


def _clean_tmp_files(location, dirs):
    for tmp_dir in dirs:
        _LOG.debug(f'Remove tmp directory {tmp_dir}')
        shutil.rmtree(build_path(location, tmp_dir), ignore_errors=True)
