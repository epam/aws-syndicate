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
import subprocess
import sys
from concurrent.futures import FIRST_EXCEPTION
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME, DEFAULT_SEP,
                                      REQ_FILE_NAME, LOCAL_REQ_FILE_NAME)
from syndicate.core.helper import (build_path, unpack_kwargs)
from syndicate.core.resources.helper import validate_params

_LOG = get_logger('python_runtime_assembler')

_PY_EXT = "*.py"


def assemble_python_lambdas(project_path, bundles_dir):
    from syndicate.core import CONFIG
    project_base_folder = os.path.basename(os.path.normpath(project_path))
    if project_path != '.':
        project_abs_path = build_path(CONFIG.project_path, project_base_folder)
    else:
        project_abs_path = CONFIG.project_path
    _LOG.info('Going to process python project by path: {0}'.format(
        project_abs_path))
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for root, sub_dirs, files in os.walk(project_abs_path):
            for item in files:
                if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                    _LOG.info('Going to build artifact in: {0}'.format(root))
                    arg = {
                        'root': str(Path(root)),
                        'config_file': str(Path(root, item)),
                        'target_folder': bundles_dir,
                        'project_path': project_path,
                    }
                    futures.append(executor.submit(_build_python_artifact, arg))
        result = concurrent.futures.wait(futures, return_when=FIRST_EXCEPTION)
    for future in result.done:
        exception = future.exception()
        if exception:
            print(f'\033[91m' + str(exception), file=sys.stderr)
            print('Likely, the solution is to assemble a bundle again',
                  file=sys.stderr)
            sys.exit(1)
    _LOG.info('Python project was processed successfully')


@unpack_kwargs
def _build_python_artifact(root, config_file, target_folder, project_path):
    _LOG.info(f'Building artifact in {target_folder}')
    with open(config_file, 'r') as file:
        lambda_config = json.load(file)
    validate_params(root, lambda_config, ['lambda_path', 'name', 'version'])
    artifact_name = f'{lambda_config["name"]}-{lambda_config["version"]}'
    artifact_path = Path(target_folder, artifact_name)
    _LOG.info(f'Artifacts path: {artifact_path}')
    os.makedirs(artifact_path, exist_ok=True)

    requirements_path = Path(root, REQ_FILE_NAME)
    if os.path.exists(requirements_path):
        _LOG.info('Going to install 3-rd party dependencies')
        try:
            subprocess.run(f"{sys.executable} -m pip install -r "
                           f"{requirements_path} -t "
                           f"{artifact_path}".split(),
                           stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            message = f'An error: \n"{e.stderr.decode()}"\noccured while ' \
                      f'installing requirements: "{str(requirements_path)}" ' \
                      f'for package "{artifact_path}"'
            _LOG.error(message)
            raise RuntimeError(message)
        _LOG.info('3-rd party dependencies were installed successfully')

    local_requirements_path = Path(root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_requirements_path):
        _LOG.info('Going to install local dependencies')
        _install_local_req(artifact_path, local_requirements_path, project_path)
        _LOG.info('Local dependencies were installed successfully')

    _LOG.info(f'Copying lambda\'s handler from {root} to {artifact_path}')
    _copy_py_files(root, artifact_path)
    package_name = build_py_package_name(lambda_config["name"],
                                         lambda_config["version"])
    _LOG.info(f'Packaging artifacts by {artifact_path} to {package_name}')
    zip_dir(str(artifact_path), str(Path(target_folder, package_name)))
    _LOG.info(f'Package \'{package_name}\' was successfully created')

    removed = False
    while not removed:
        _LOG.info(f'Trying to remove "{artifact_path}"')
        try:
            shutil.rmtree(artifact_path)
            removed = True
        except Exception as e:
            _LOG.warn(f'An error "{e}" occured while '
                      f'removing artifacts "{artifact_path}"')
    _LOG.info(f'"{artifact_path}" was removed successfully')


def _install_local_req(artifact_path, local_req_path, project_path):
    from syndicate.core import CONFIG
    with open(local_req_path) as f:
        local_req_list = f.readlines()
    local_req_list = [path_resolver(r.strip()) for r in local_req_list]
    _LOG.info(f'Installing local dependencies: {local_req_list}')
    # copy folders
    for lrp in local_req_list:
        _LOG.info(f'Processing local dependency: {lrp}')
        shutil.copytree(Path(CONFIG.project_path, project_path, lrp),
                        Path(artifact_path, lrp), dirs_exist_ok=True)
        _LOG.debug('Dependency was copied successfully')

        folders = [r for r in lrp.split(DEFAULT_SEP) if r]
        # process folder from root python project
        folders.insert(0, '')
        i = 0
        temp_path = ''
        while i < len(folders):
            temp_path += DEFAULT_SEP + folders[i]
            src_path = Path(CONFIG.project_path, project_path,temp_path)
            dst_path = Path(artifact_path, temp_path)
            _copy_py_files(str(src_path), str(dst_path))
            i += 1
        _LOG.debug('Python files from packages were copied successfully')


def _copy_py_files(search_path, destination_path):
    files = glob.iglob(build_path(search_path, _PY_EXT))
    for py_file in files:
        if os.path.isfile(py_file):
            shutil.copy2(py_file, destination_path)
