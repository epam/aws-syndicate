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
import json
import os
import shutil
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME,
                                      NODE_REQ_FILE_NAME)
from syndicate.core.helper import (build_path, unpack_kwargs,
                                   execute_command_by_path)
from syndicate.core.resources.helper import validate_params

_LOG = get_logger('nodejs_runtime_assembler')


def assemble_node_lambdas(project_path, bundles_dir):
    from syndicate.core import CONFIG
    project_abs_path = Path(CONFIG.project_path, project_path)
    _LOG.info('Going to package lambdas starting by path {0}'.format(
        project_abs_path))
    executor = ThreadPoolExecutor(max_workers=5)
    futures = []
    for root, sub_dirs, files in os.walk(project_abs_path):
        for item in files:
            if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                _LOG.info('Going to build artifact in: {0}'.format(root))
                arg = {
                    'item': item,
                    'root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(_build_node_artifact, arg))
    for future in concurrent.futures.as_completed(futures):
        _LOG.info(future.result())


@unpack_kwargs
def _build_node_artifact(item, root, target_folder):
    _check_npm_is_installed()
    _LOG.debug('Building artifact in {0}'.format(target_folder))
    lambda_config_dict = json.load(open(build_path(root, item)))
    _LOG.debug('Root path: {}'.format(root))
    req_params = ['lambda_path', 'name', 'version']
    validate_params(root, lambda_config_dict, req_params)
    lambda_name = lambda_config_dict['name']
    lambda_version = lambda_config_dict['version']
    artifact_name = lambda_name + '-' + lambda_version
    # create folder to store artifacts
    artifact_path = build_path(target_folder, artifact_name)
    _LOG.debug('Artifacts path: {0}'.format(artifact_path))
    if not os.path.exists(artifact_path):
        os.makedirs(artifact_path)
    _LOG.debug('Folders are created')
    # getting file content
    req_path = Path(root, NODE_REQ_FILE_NAME)
    try:
        if os.path.exists(req_path):
            command = 'npm install'
            execute_command_by_path(command=command, path=root)
            _LOG.debug('3-rd party dependencies were installed successfully')

        package_name = build_py_package_name(lambda_name, lambda_version)
        zip_dir(root, build_path(target_folder, package_name))
        lock = threading.RLock()
        lock.acquire()
        try:
            # remove unused folder/files
            node_modules_path = os.path.join(root, 'node_modules')
            if os.path.exists(node_modules_path):
                shutil.rmtree(node_modules_path)
            # todo Investigate deleting package_lock file
            # shutil.rmtree(os.path.join(root, 'package_lock.json'))
            shutil.rmtree(artifact_path)
        except FileNotFoundError as e:
            _LOG.exception('Error occurred while temp files removing.')
        finally:
            lock.release()
        return 'Lambda package {0} was created successfully'.format(
            package_name)
    except Exception:
        _LOG.exception(
            'Error occurred during the \'{0}\' lambda deployment package '
            'assembling'.format(lambda_name))
        return 'Error occurred during the \'{0}\' lambda deployment package ' \
               'assembling'.format(lambda_name)


def _check_npm_is_installed():
    import subprocess
    result = subprocess.call('npm -v', shell=True)
    if result:
        raise AssertionError(
            'NPM is not installed. There is no ability to build '
            'NodeJS bundle. Please, install npm are retry to build bundle.')
