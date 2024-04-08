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
import concurrent
import glob
import json
import os
import shutil
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from distutils.dir_util import copy_tree
from distutils.errors import DistutilsFileError
from pathlib import Path

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME,
                                      NODE_REQ_FILE_NAME,
                                      LAMBDA_LAYER_CONFIG_FILE_NAME,
                                      NODE_LAMBDA_LAYER_PATH, DEFAULT_SEP,
                                      LOCAL_REQ_FILE_NAME)
from syndicate.core.groups import RUNTIME_NODEJS
from syndicate.core.helper import (build_path, unpack_kwargs,
                                   execute_command_by_path, without_zip_ext,
                                   zip_ext)
from syndicate.core.project_state.project_state import BUILD_MAPPINGS
from syndicate.core.resources.helper import validate_params

_LOG = get_logger('nodejs_runtime_assembler')


_JS_EXT = "*.js"
DEPENDENCIES_FOLDER = 'node_modules'


def _copy_js_files(search_path, destination_path):
    files = glob.iglob(build_path(search_path, _JS_EXT))
    for js_file in files:
        if os.path.isfile(js_file):
            shutil.copy2(js_file, destination_path)


def assemble_node_lambdas(project_path, bundles_dir):
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
                futures.append(executor.submit(_build_node_artifact, arg))
            elif item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
                _LOG.info(f'Going to build lambda layer in `{root}`')
                arg = {
                    'layer_root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(build_node_lambda_layer, arg))
    for future in concurrent.futures.as_completed(futures):
        _LOG.info(future.result())


@unpack_kwargs
def _build_node_artifact(item, root, target_folder):
    _check_npm_is_installed()
    _LOG.debug(f'Building artifact in {target_folder}')
    lambda_config_dict = json.load(open(build_path(root, item)))
    _LOG.debug(f'Root path: {root}')
    req_params = ['lambda_path', 'name', 'version']
    validate_params(root, lambda_config_dict, req_params)
    lambda_name = lambda_config_dict['name']
    lambda_version = lambda_config_dict['version']
    artifact_name = lambda_name + '-' + lambda_version
    package_name = build_py_package_name(lambda_name, lambda_version)
    artifact_path = str(Path(target_folder, artifact_name))

    copy_tree(root, str(Path(artifact_path, 'lambdas', lambda_name)))
    install_requirements(root, target_folder, artifact_path, package_name)


@unpack_kwargs
def build_node_lambda_layer(layer_root: str, target_folder: str):
    with open(Path(layer_root, LAMBDA_LAYER_CONFIG_FILE_NAME), 'r') as file:
        layer_config = json.load(file)

    validate_params(layer_root, layer_config, ['name', 'deployment_package'])
    artifact_name = without_zip_ext(layer_config['deployment_package'])
    package_name = zip_ext(layer_config['deployment_package'])
    artifact_path = str(Path(target_folder, artifact_name))

    copy_tree(layer_root, artifact_path)
    install_requirements(layer_root, target_folder, artifact_path,
                         package_name, is_layer=True)


def install_requirements(root: str, target_folder: str, artifact_path: str,
                         package_name: str, is_layer=False):
    """
    artifact_path: str - Absolute archive path
    root: str - lambda folder (src/lambdas/{$lambda_name})
    """
    _LOG.info(f'Artifacts path: {artifact_path}')
    os.makedirs(artifact_path, exist_ok=True)
    if not os.path.exists(artifact_path):
        os.makedirs(artifact_path)
    _LOG.debug('Folders are created')
    # getting file content
    req_path = Path(root, NODE_REQ_FILE_NAME)

    try:
        if os.path.exists(req_path):
            command = 'npm install'
            # this command creates 'node_modules' folder in lambda folder
            execute_command_by_path(command=command, path=root)
            _LOG.debug('3-rd party dependencies were installed successfully')
            try:
                copy_tree(str(Path(root, DEPENDENCIES_FOLDER)),
                          str(Path(artifact_path, DEPENDENCIES_FOLDER)))
            except DistutilsFileError:
                _LOG.info('No dependencies folder - nothing to copy.')
            except Exception as e:
                _LOG.exception(f'Error occurred while lambda files coping: {e}')

        # install local requirements
        local_requirements_path = Path(root, LOCAL_REQ_FILE_NAME)
        if os.path.exists(local_requirements_path):
            _LOG.info('Going to install local dependencies')
            _copy_local_req(artifact_path, local_requirements_path)
            _LOG.info('Local dependencies were installed successfully')

        if is_layer:
            zip_dir(artifact_path,
                    str(build_path(target_folder, package_name)),
                    NODE_LAMBDA_LAYER_PATH)
        else:
            zip_dir(artifact_path,
                    build_path(target_folder, package_name))

        lock = threading.RLock()
        lock.acquire()
        try:
            # remove unused folder/files
            node_modules_path = os.path.join(root, DEPENDENCIES_FOLDER)
            if os.path.exists(node_modules_path):
                shutil.rmtree(node_modules_path)
            # todo Investigate deleting package_lock file
            # shutil.rmtree(os.path.join(root, 'package_lock.json'))
            shutil.rmtree(artifact_path)
        except FileNotFoundError as e:
            _LOG.exception(f'Error occurred while temp files removing: {e}')
        finally:
            lock.release()
        return f'Lambda package {package_name} was created successfully'
    except Exception as e:
        _msg = 'Error occurred during the lambda layer deployment package ' \
               'assembling'
        _LOG.exception(f'{_msg}: {e}')
        return _msg


def _check_npm_is_installed():
    import subprocess
    result = subprocess.call('npm -v', shell=True)
    if result:
        raise AssertionError(
            'NPM is not installed. There is no ability to build '
            'NodeJS bundle. Please, install npm and retry to build bundle.')


def _copy_local_req(artifact_path, local_req_path):
    from syndicate.core import CONFIG
    with open(local_req_path) as f:
        local_req_list = f.readlines()
    local_req_list = [path_resolver(r.strip()) for r in local_req_list]
    _LOG.info(f'Installing local dependencies: {local_req_list}')
    # copy folders
    for lrp in local_req_list:
        _LOG.info(f'Processing local dependency: {lrp}')
        copy_tree(str(Path(CONFIG.project_path,
                           BUILD_MAPPINGS[RUNTIME_NODEJS],
                           lrp)),
                  str(Path(artifact_path, lrp)))
        _LOG.debug('Dependency was copied successfully')

        folders = [r for r in lrp.split(DEFAULT_SEP) if r]
        # process folder from root project
        folders.insert(0, '')
        for folder in folders:
            src_path = Path(CONFIG.project_path,
                            BUILD_MAPPINGS[RUNTIME_NODEJS], folder)
            dst_path = Path(artifact_path, folder)
            _copy_js_files(str(src_path), str(dst_path))
        _LOG.debug('JavaScript files from packages were copied successfully')
