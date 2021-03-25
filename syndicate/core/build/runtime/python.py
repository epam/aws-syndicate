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
from concurrent.futures import ALL_COMPLETED
from concurrent.futures.thread import ThreadPoolExecutor
from distutils import dir_util

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME,
                                      REQ_FILE_NAME, LOCAL_REQ_FILE_NAME,
                                      DEFAULT_SEP)
from syndicate.core.helper import (build_path, unpack_kwargs, execute_command,
                                   prettify_json)
from syndicate.core.resources.helper import validate_params

_LOG = get_logger('python_runtime_assembler')

_PY_EXT = "*.py"


def assemble_python_lambdas(project_path, bundles_dir):
    from syndicate.core import CONFIG
    project_base_folder = os.path.basename(os.path.normpath(project_path))
    if project_path != '.':
        project_abs_path = build_path(CONFIG.project_path, project_path)
    else:
        project_abs_path = CONFIG.project_path
    _LOG.info('Going to process python project by path: {0}'.format(
        project_abs_path))
    executor = ThreadPoolExecutor(max_workers=5)
    futures = []
    for root, sub_dirs, files in os.walk(project_abs_path):
        for item in files:
            if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                _LOG.info('Going to build artifact in: {0}'.format(root))
                arg = {
                    'item': item,
                    'project_base_folder': project_base_folder,
                    'project_path': project_path,
                    'root': root,
                    'target_folder': bundles_dir
                }
                futures.append(executor.submit(_build_python_artifact, arg))
    concurrent.futures.wait(futures, return_when=ALL_COMPLETED)
    executor.shutdown()
    _LOG.info('Python project was processed successfully')


@unpack_kwargs
def _build_python_artifact(item, project_base_folder, project_path, root,
                           target_folder):
    from syndicate.core import CONFIG
    _LOG.debug('Building artifact in {0}'.format(target_folder))
    lambda_config_dict = json.load(open(build_path(root, item)))
    req_params = ['lambda_path', 'name', 'version']
    validate_params(root, lambda_config_dict, req_params)
    lambda_path = path_resolver(lambda_config_dict['lambda_path'])
    lambda_name = lambda_config_dict['name']
    lambda_version = lambda_config_dict['version']
    artifact_name = lambda_name + '-' + lambda_version
    # create folder to store artifacts
    artifact_path = build_path(target_folder, artifact_name)
    _LOG.debug('Artifacts path: {0}'.format(artifact_path))
    if not os.path.isdir(artifact_path):
        os.makedirs(artifact_path)
    _LOG.debug('Folders are created')
    # install requirements.txt content
    # getting file content
    req_path = build_path(root, REQ_FILE_NAME)
    if os.path.exists(req_path):
        _LOG.debug('Going to install 3-rd party dependencies')
        with open(req_path) as f:
            req_list = f.readlines()
        req_list = [path_resolver(r.strip()) for r in req_list]
        _LOG.debug(str(req_list))
        # install dependencies
        for lib in req_list:
            command = 'pip3.9 install {0} -t {1}'.format(lib, artifact_path)
            execute_command(command=command)
        _LOG.debug('3-rd party dependencies were installed successfully')

    # install local requirements
    local_req_path = build_path(root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_req_path):
        _LOG.debug('Going to install local dependencies')
        _install_local_req(artifact_path, local_req_path, project_base_folder,
                           project_path)
        _LOG.debug('Local dependencies were installed successfully')
    src_path = build_path(CONFIG.project_path, project_path, lambda_path)
    _copy_py_files(src_path, artifact_path)
    package_name = build_py_package_name(lambda_name, lambda_version)
    zip_dir(artifact_path, build_path(target_folder, package_name))
    # remove unused folder
    lock = threading.RLock()
    lock.acquire()
    try:
        shutil.rmtree(artifact_path)
    finally:
        lock.release()
    _LOG.info('Package {0} was created successfully'.format(package_name))


def _install_local_req(artifact_path, local_req_path, project_base_folder,
                       project_path):
    from syndicate.core import CONFIG
    with open(local_req_path) as f:
        local_req_list = f.readlines()
    local_req_list = [path_resolver(r.strip()) for r in local_req_list]
    _LOG.info('Local dependencies: {0}'.format(prettify_json(local_req_list)))
    # copy folders
    for lrp in local_req_list:
        _LOG.info('Processing dependency: {0}'.format(lrp))
        folder_path = build_path(artifact_path, project_base_folder, lrp)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        dir_util.copy_tree(build_path(CONFIG.project_path, project_path, lrp),
                           folder_path)
        _LOG.debug('Dependency was copied successfully')

        folders = [r for r in lrp.split(DEFAULT_SEP) if r]
        # process folder from root python project
        folders.insert(0, '')
        i = 0
        temp_path = ''
        while i < len(folders):
            temp_path += DEFAULT_SEP + folders[i]
            src_path = build_path(CONFIG.project_path, project_path,
                                  temp_path)
            dst_path = build_path(artifact_path, project_base_folder,
                                  temp_path)
            _copy_py_files(src_path, dst_path)
            i += 1
        _LOG.debug('Python files from packages were copied successfully')


def _copy_py_files(search_path, destination_path):
    files = glob.iglob(build_path(search_path, _PY_EXT))
    for py_file in files:
        if os.path.isfile(py_file):
            shutil.copy2(py_file, destination_path)
