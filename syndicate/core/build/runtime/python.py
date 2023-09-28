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
import platform
import shutil
import subprocess
import sys
from concurrent.futures import FIRST_EXCEPTION
from concurrent.futures import FIRST_EXCEPTION
from concurrent.futures.thread import ThreadPoolExecutor
from distutils.dir_util import copy_tree
from itertools import chain
from pathlib import Path
from typing import Union, Optional, List, Set

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME, DEFAULT_SEP,
                                      REQ_FILE_NAME, LOCAL_REQ_FILE_NAME,
                                      LAMBDA_LAYER_CONFIG_FILE_NAME,
                                      PYTHON_LAMBDA_LAYER_PATH,
                                      MANY_LINUX_2014_PLATFORM)
from syndicate.core.helper import (build_path, unpack_kwargs, zip_ext,
                                   without_zip_ext)
from syndicate.core.resources.helper import validate_params

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

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
    with ThreadPoolExecutor(max_workers=5) as executor:
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
                    futures.append(
                        executor.submit(_build_python_artifact, arg))
                elif item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
                    _LOG.info(f'Going to build lambda layer in `{root}`')
                    arg = {
                        'layer_root': root,
                        'bundle_dir': bundles_dir,
                        'project_path': project_path
                    }
                    futures.append(
                        executor.submit(build_python_lambda_layer, arg))
        result = concurrent.futures.wait(futures, return_when=FIRST_EXCEPTION)
    for future in result.done:
        exception = future.exception()
        if exception:
            print(f'\033[91m' + str(exception), file=sys.stderr)
            sys.exit(1)
    _LOG.info('Python project was processed successfully')


def remove_dir(path: Union[str, Path]):
    removed = False
    while not removed:
        _LOG.info(f'Trying to remove "{path}"')
        try:
            shutil.rmtree(path)
            removed = True
        except Exception as e:
            _LOG.warn(f'An error "{e}" occurred while '
                      f'removing artifacts "{path}"')


@unpack_kwargs
def build_python_lambda_layer(layer_root: str, bundle_dir: str,
                              project_path: str):
    """
    Layer root is a dir where these files exist:
    - lambda_layer_config.json
    - local_requirements.txt
    - requirements.txt
    """
    with open(Path(layer_root, LAMBDA_LAYER_CONFIG_FILE_NAME), 'r') as file:
        layer_config = json.load(file)
    validate_params(layer_root, layer_config, ['name', 'deployment_package'])
    artifact_name = without_zip_ext(layer_config['deployment_package'])
    artifact_path = Path(bundle_dir, artifact_name)
    path_for_requirements = artifact_path / PYTHON_LAMBDA_LAYER_PATH
    _LOG.info(f'Artifacts path: {artifact_path}')
    os.makedirs(artifact_path, exist_ok=True)

    # install requirements.txt content
    requirements_path = Path(layer_root, REQ_FILE_NAME)
    if os.path.exists(requirements_path):
        install_requirements_to(requirements_path, to=path_for_requirements,
                                config=layer_config)

    # install local requirements
    local_requirements_path = Path(layer_root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_requirements_path):
        _LOG.info('Going to install local dependencies')
        _install_local_req(path_for_requirements, local_requirements_path,
                           project_path)
        _LOG.info('Local dependencies were installed successfully')

    # making zip archive
    package_name = zip_ext(layer_config['deployment_package'])
    _LOG.info(f'Packaging artifacts by {artifact_path} to {package_name}')
    zip_dir(str(artifact_path), str(Path(bundle_dir, package_name)))
    _LOG.info(f'Package \'{package_name}\' was successfully created')
    # remove unused folder
    remove_dir(artifact_path)
    _LOG.info(f'"{artifact_path}" was removed successfully')


@unpack_kwargs
def _build_python_artifact(root, config_file, target_folder, project_path):
    _LOG.info(f'Building artifact in {target_folder}')

    # create folder to store artifacts
    with open(config_file, 'r') as file:
        lambda_config = json.load(file)
    validate_params(root, lambda_config, ['lambda_path', 'name', 'version'])
    artifact_name = f'{lambda_config["name"]}-{lambda_config["version"]}'
    artifact_path = Path(target_folder, artifact_name)
    _LOG.info(f'Artifacts path: {artifact_path}')
    os.makedirs(artifact_path, exist_ok=True)

    # install requirements.txt content
    requirements_path = Path(root, REQ_FILE_NAME)
    if os.path.exists(requirements_path):
        install_requirements_to(requirements_path, to=artifact_path,
                                config=lambda_config)

    # install local requirements
    local_requirements_path = Path(root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_requirements_path):
        _LOG.info('Going to install local dependencies')
        _install_local_req(artifact_path, local_requirements_path,
                           project_path)
        _LOG.info('Local dependencies were installed successfully')

    # copy lambda's specific packages
    packages_dir = artifact_path / 'lambdas' / Path(root).name
    os.makedirs(packages_dir, exist_ok=True)
    for package in filter(
            is_python_package,
            [Path(root, item) for item in os.listdir(root)]):
        _LOG.info(f'Copying package {package} to lambda\'s artifacts packages '
                  f'dir: {packages_dir}')
        copy_tree(str(package), str(packages_dir / package.name))
        _LOG.info('Copied successfully')

    # copy lambda's handler to artifacts folder
    _LOG.info(f'Copying lambda\'s handler from {root} to {artifact_path}')
    _copy_py_files(root, artifact_path)

    # making zip archive
    package_name = build_py_package_name(lambda_config["name"],
                                         lambda_config["version"])
    _LOG.info(f'Packaging artifacts by {artifact_path} to {package_name}')
    zip_dir(str(artifact_path), str(Path(target_folder, package_name)))
    _LOG.info(f'Package \'{package_name}\' was successfully created')

    # remove unused folder
    remove_dir(artifact_path)
    _LOG.info(f'"{artifact_path}" was removed successfully')


def install_requirements_to(requirements_txt: Union[str, Path],
                            to: Union[str, Path],
                            config: Optional[dict] = None):
    config = config or {}
    _LOG.info('Going to install 3-rd party dependencies')
    supported_platforms = update_platforms(set(config.get('platforms') or []))
    python_version = _get_python_version(lambda_config=config)
    try:
        if supported_platforms:
            # tries to install packages compatible with specific platforms
            # returns the list of requirement that failed the installation
            failed_requirements = install_requirements_for_platform(
                requirements_txt=requirements_txt,
                to=to,
                supported_platforms=supported_platforms,
                python_version=python_version
            )
            for failed in failed_requirements:
                command = build_pip_install_command(  # default installation
                    requirement=failed,
                    to=to,
                )
                subprocess.run(command, stderr=subprocess.PIPE, check=True)
        else:
            _LOG.info('Installing all the requirements with defaults')
            command = build_pip_install_command(
                requirement=requirements_txt,
                to=to
            )
            subprocess.run(command, stderr=subprocess.PIPE, check=True)

    except subprocess.CalledProcessError as e:
        message = f'An error: \n"{e.stderr.decode()}"\noccured while ' \
                  f'installing requirements: "{str(requirements_txt)}" ' \
                  f'for package "{to}"'
        _LOG.error(message)
        raise RuntimeError(message)
    _LOG.info('3-rd party dependencies were installed successfully')


def build_pip_install_command(
        requirement: Optional[Union[str, Path]],
        to: Optional[Union[str, Path]] = None,
        implementation: Optional[str] = None,
        python: Optional[str] = None,
        only_binary: Optional[str] = None,
        platforms: Optional[Set[str]] = None,
        additional_args: Optional[List[str]] = None) -> List[str]:
    """
    :param requirement: path to requirements.txt or just one requirement.
    If the path is not file or does not exist it will be treated as one
    requirement.
    :param to: Optional[str] the path where to install requirements
    :param implementation: Optional[str], can be `cp`
    :param python: Optional[str], can be `3.8`, `3.9`
    :param only_binary: Optional[str], can be `:all:` or `:none:`
    :param platforms: Optional[Set], can be {'manylinux2014_x86_64'}
    :param additional_args: Optional[List[str]] list or some additional args
    :return: List[str]
    """
    command = [
        sys.executable, '-m', 'pip', 'install'
    ]
    r_path = Path(requirement)
    if r_path.exists() and r_path.is_file():
        command.extend(['-r', str(r_path)])
    else:  # not a path to requirements.txt but one requirement
        command.append(requirement)

    if to:
        command.extend(['-t', str(to)])
    if implementation:
        command.extend(['--implementation', 'cp'])
    if python:
        command.extend(['--python-version', python])
    if only_binary:
        command.append(f'--only-binary={only_binary}')
    if platforms:
        command.extend(chain.from_iterable(
            ('--platform', p) for p in platforms
        ))
    command.extend(additional_args or [])
    return command


def update_platforms(platforms: Set[str]) -> Set[str]:
    """
    If platforms are not empty, just return them without changing
    (user's choice). But in case the set is empty and the current
    processor is ARM (mac m1) or OS is Windows, we add
    manylinux2014_x86_64 to the list of platforms because by default
    lambdas with x86_64.
    This code is experimental and can be adjusted
    """
    if platforms:
        return platforms
    _arm = platform.processor() == 'arm'
    _win = platform.system() == 'Windows'
    if _arm or _win:
        platforms.add(MANY_LINUX_2014_PLATFORM)
    return platforms


def install_requirements_for_platform(requirements_txt: Union[str, Path],
                                      to: Union[str, Path],
                                      python_version: str,
                                      supported_platforms: Set[str]
                                      ) -> List[str]:
    _LOG.info(f'Going to install 3-rd party dependencies for platforms: '
              f'{",".join(supported_platforms)}')
    fp = open(requirements_txt, 'r')
    it = (
        line.split(' #')[0].strip() for line in
        filter(lambda line: not line.strip().startswith('#'), fp)
    )
    failed_requirements = []
    for requirement in it:
        try:
            command = build_pip_install_command(
                requirement=requirement,
                to=to,
                implementation='cp',
                python=python_version,
                only_binary=':all:',
                platforms=supported_platforms
            )
            subprocess.run(command, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            message = f'An error: \n"{e.stderr.decode()}"\noccured while ' \
                      f'installing requirements for platforms:' \
                      f'{",".join(supported_platforms)}: ' \
                      f'"{str(requirements_txt)}" for package "{requirement}"'
            USER_LOG.warning(f"\033[93m{message}\033[0m")
            failed_requirements.append(requirement)
    fp.close()
    return failed_requirements


def _install_local_req(artifact_path, local_req_path, project_path):
    from syndicate.core import CONFIG
    with open(local_req_path) as f:
        local_req_list = f.readlines()
    local_req_list = [path_resolver(r.strip()) for r in local_req_list]
    _LOG.info(f'Installing local dependencies: {local_req_list}')
    # copy folders
    for lrp in local_req_list:
        _LOG.info(f'Processing local dependency: {lrp}')
        copy_tree(str(Path(CONFIG.project_path, project_path, lrp)),
                  str(Path(artifact_path, lrp)))
        _LOG.debug('Dependency was copied successfully')

        folders = [r for r in lrp.split(DEFAULT_SEP) if r]
        # process folder from root python project
        folders.insert(0, '')
        i = 0
        temp_path = ''
        while i < len(folders):
            temp_path += DEFAULT_SEP + folders[i]
            src_path = Path(CONFIG.project_path, project_path, temp_path)
            dst_path = Path(artifact_path, temp_path)
            _copy_py_files(str(src_path), str(dst_path))
            i += 1
        _LOG.debug('Python files from packages were copied successfully')


def _get_python_version(lambda_config: dict) -> Optional[str]:
    """
    Lambda config or layer config.
     "runtime": "python3.7" => "3.7".
    If "runtime" contains a list with runtimes. The lowest version is returned
    """
    runtimes: Union[None, List, str] = lambda_config.get('runtime')
    if not runtimes:
        return
    if isinstance(runtimes, str):
        runtimes = [runtimes]
    return sorted(
        ''.join(ch for ch in runtime if ch.isdigit() or ch == '.')
        for runtime in runtimes
    )[0]


def _copy_py_files(search_path, destination_path):
    files = glob.iglob(build_path(search_path, _PY_EXT))
    for py_file in files:
        if os.path.isfile(py_file):
            shutil.copy2(py_file, destination_path)


def is_python_package(path: Union[Path, str]) -> bool:
    """A file is considered to be a package if it's a directory containing
    __init__.py"""
    return os.path.isdir(path) and os.path.exists(Path(path, '__init__.py'))
