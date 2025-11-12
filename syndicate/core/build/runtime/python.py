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
from itertools import chain
from pathlib import Path
from typing import Union, Optional, List, Set

from syndicate.exceptions import ArtifactAssemblingError, InvalidTypeError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.helper import build_py_package_name, zip_dir, \
    remove_dir, resolve_bundles_cache_directory, merge_zip_files
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (LAMBDA_CONFIG_FILE_NAME, DEFAULT_SEP,
                                      REQ_FILE_NAME, LOCAL_REQ_FILE_NAME,
                                      LAMBDA_LAYER_CONFIG_FILE_NAME,
                                      PYTHON_LAMBDA_LAYER_PATH,
                                      MANY_LINUX_2014_PLATFORM)
from syndicate.core.helper import (build_path, unpack_kwargs, zip_ext,
                                   without_zip_ext, compute_file_hash)
from syndicate.core.resources.helper import validate_params
from syndicate.core.groups import PYTHON_ROOT_DIR_SRC


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

_PY_EXT = "*.py"
EMPTY_LINE_CHARS = ('\n', '\r\n', '\t')

REQ_HASH_SUFFIX = 'r_hash'
EMPTY_FILE_HASH = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
TMP_DIR = 'tmp'


def assemble_python_lambdas(
    runtime_root_dir: str, 
    bundles_dir: str, 
    errors_allowed: bool,
    **kwargs
) -> None:
    from syndicate.core import CONFIG

    runtime_base_dir = os.path.basename(os.path.normpath(runtime_root_dir))
    if runtime_root_dir != '.':
        runtime_abs_path = build_path(CONFIG.project_path, runtime_base_dir)
    else:
        runtime_abs_path = CONFIG.project_path

    if runtime_root_dir != PYTHON_ROOT_DIR_SRC:
        runtime_abs_path = os.path.join(runtime_abs_path, PYTHON_ROOT_DIR_SRC)

    _LOG.info(f'Going to process python project by path: {runtime_abs_path}')

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for root, _, files in os.walk(runtime_abs_path):
            for item in files:
                if item.endswith(LAMBDA_CONFIG_FILE_NAME):
                    _LOG.info(f'Going to build artifact in: {root!r}')
                    arg = {
                        'root': str(Path(root)),
                        'config_file': str(Path(root, item)),
                        'target_folder': bundles_dir,
                        'runtime_root_dir': runtime_root_dir,
                        'errors_allowed': errors_allowed
                    }
                    futures.append(
                        executor.submit(_build_python_artifact, arg))
                elif item.endswith(LAMBDA_LAYER_CONFIG_FILE_NAME):
                    _LOG.info(f'Going to build lambda layer in {root!r}')
                    arg = {
                        'layer_root': root,
                        'bundle_dir': bundles_dir,
                        'runtime_root_dir': runtime_root_dir,
                        'errors_allowed': errors_allowed
                    }
                    futures.append(
                        executor.submit(build_python_lambda_layer, arg))
        result = concurrent.futures.wait(futures, return_when=FIRST_EXCEPTION)
    for future in result.done:
        exception = future.exception()
        if exception:
            raise ArtifactAssemblingError(exception)
    _LOG.info('Python project was processed successfully')


@unpack_kwargs
def build_python_lambda_layer(
    layer_root: str, 
    bundle_dir: str,
    runtime_root_dir: str,
    errors_allowed: bool
) -> None:
    """
    Layer root is a dir where these files exist:
    - lambda_layer_config.json
    - local_requirements.txt
    - requirements.txt
    """
    cache_dir_path = resolve_bundles_cache_directory()
    os.makedirs(cache_dir_path, exist_ok=True)

    with open(Path(layer_root, LAMBDA_LAYER_CONFIG_FILE_NAME), 'r') as file:
        layer_config = json.load(file)
    validate_params(layer_root, layer_config, ['name', 'deployment_package'])
    artifact_name = without_zip_ext(layer_config['deployment_package'])
    artifact_path = Path(bundle_dir, artifact_name)

    _LOG.info(f"Going to assemble lambda layer '{layer_config['name']}'")
    package_name = zip_ext(layer_config['deployment_package'])

    r_hash_name = f'.{artifact_name}_{REQ_HASH_SUFFIX}'
    artifact_cache_path = Path(cache_dir_path, artifact_name)

    prev_req_hash = None
    req_hash_path = Path(cache_dir_path, r_hash_name)
    if os.path.exists(req_hash_path):
        with open(req_hash_path, 'r') as f:
            prev_req_hash = f.read().strip()

    # install requirements.txt content
    requirements_path = Path(layer_root, REQ_FILE_NAME)
    if os.path.exists(requirements_path):
        current_req_hash = compute_file_hash(requirements_path)
        if (current_req_hash != EMPTY_FILE_HASH and
                prev_req_hash != current_req_hash):
            _LOG.debug(f'Artifacts cache path: {artifact_cache_path}')
            os.makedirs(artifact_cache_path, exist_ok=True)

            install_requirements_to(requirements_path, to=artifact_cache_path,
                                    config=layer_config,
                                    errors_allowed=errors_allowed)

            _LOG.debug('Zipping 3-rd party dependencies')
            zip_dir(str(artifact_cache_path),
                    str(Path(cache_dir_path, package_name)))

            remove_dir(artifact_cache_path)
            _LOG.debug(f'"{artifact_cache_path}" was removed successfully')

            with open(req_hash_path, 'w') as f:
                f.write(current_req_hash)
                _LOG.debug(f'Updated requirements hash to {current_req_hash}')
        else:
            _LOG.info(
                f"Skipping installation from the '{requirements_path}' "
                f"because no changes detected from the previous run")

    # install local requirements
    local_requirements_path = Path(layer_root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_requirements_path):
        tmp_artifact_path = Path(bundle_dir, artifact_name, TMP_DIR)

        _LOG.info(f'Artifacts path: {tmp_artifact_path}')
        os.makedirs(tmp_artifact_path, exist_ok=True)

        _LOG.info('Going to install local dependencies')
        _install_local_req(tmp_artifact_path, local_requirements_path,
                           runtime_root_dir)
        _LOG.info('Local dependencies were installed successfully')

        # making zip archive
        _LOG.info(
            f'Packaging artifacts by {tmp_artifact_path} to {package_name}')
        zip_dir(str(tmp_artifact_path),
                str(Path(artifact_path, package_name)))

    if (Path(cache_dir_path, package_name).exists() or
            Path(artifact_path, package_name).exists()):
        _LOG.info(f"Merging lambda layer code with 3-rd party dependencies")
        merge_zip_files(str(Path(artifact_path, package_name)),
                        str(Path(cache_dir_path, package_name)),
                        str(Path(bundle_dir, package_name)),
                        output_subfolder=PYTHON_LAMBDA_LAYER_PATH)
    else:
        raise ArtifactAssemblingError(
            f"Layer package cannot be empty. "
            f"Please check the layer '{layer_config['name']}' configuration.")

    _LOG.info(f'Package \'{package_name}\' was successfully created')

    # remove unused folder
    remove_dir(artifact_path)
    _LOG.info(f'"{artifact_path}" was removed successfully')


@unpack_kwargs
def _build_python_artifact(
    runtime_root_dir: str,
    errors_allowed: bool,
    target_folder: str,
    config_file: str,
    root: str,
) -> None:
    _LOG.info(f'Building artifact in {target_folder}')

    cache_dir_path = resolve_bundles_cache_directory()
    os.makedirs(cache_dir_path, exist_ok=True)

    # create folder to store artifacts
    with open(config_file, 'r') as file:
        lambda_config = json.load(file)
    validate_params(root, lambda_config, ['lambda_path', 'name', 'version'])

    lambda_name = lambda_config['name']
    artifact_name = f'{lambda_name}-{lambda_config["version"]}'
    artifact_path = Path(target_folder, artifact_name)
    tmp_artifact_path = Path(target_folder, artifact_name, TMP_DIR)

    _LOG.info(f"Going to assemble lambda '{lambda_name}'")
    package_name = build_py_package_name(lambda_name, lambda_config["version"])

    r_hash_name = f'.{artifact_name}_{REQ_HASH_SUFFIX}'
    artifact_cache_path = Path(cache_dir_path, artifact_name)

    _LOG.info(f'Artifacts path: {artifact_path}')
    os.makedirs(tmp_artifact_path, exist_ok=True)

    prev_req_hash = None
    req_hash_path = Path(cache_dir_path, r_hash_name)
    if os.path.exists(req_hash_path):
        with open(req_hash_path, 'r') as f:
            prev_req_hash = f.read().strip()

    # install requirements.txt content
    requirements_path = Path(root, REQ_FILE_NAME)
    if os.path.exists(requirements_path):
        current_req_hash = compute_file_hash(requirements_path)
        if (current_req_hash != EMPTY_FILE_HASH and
                prev_req_hash != current_req_hash):
            _LOG.debug(f'Artifacts cache path: {artifact_cache_path}')
            os.makedirs(artifact_cache_path, exist_ok=True)
            
            install_requirements_to(requirements_path, to=artifact_cache_path,
                                    config=lambda_config,
                                    errors_allowed=errors_allowed)
            _LOG.debug(
                f'Zipping 3-rd party dependencies in {artifact_cache_path}')
            zip_dir(str(artifact_cache_path), 
                    str(Path(cache_dir_path, package_name)))

            remove_dir(artifact_cache_path)
            _LOG.debug(f'"{artifact_cache_path}" was removed successfully')
            
            with open(req_hash_path, 'w') as f:
                f.write(current_req_hash)
                _LOG.debug(f'Updated requirements hash to {current_req_hash}')
        else:
            _LOG.info(
                f"Skipping installation from the '{requirements_path}' "
                f"because no changes detected from the previous run")

    # install local requirements
    local_requirements_path = Path(root, LOCAL_REQ_FILE_NAME)
    if os.path.exists(local_requirements_path):
        _LOG.info('Going to install local dependencies')
        _install_local_req(tmp_artifact_path, local_requirements_path,
                           runtime_root_dir)
        _LOG.info('Local dependencies were installed successfully')

    # copy lambda's specific packages
    packages_dir = tmp_artifact_path / 'lambdas' / Path(root).name
    os.makedirs(packages_dir, exist_ok=True)
    for package in filter(
            is_python_package,
            [Path(root, item) for item in os.listdir(root)]):
        _LOG.info(f'Copying package {package} to lambda\'s artifacts packages '
                  f'dir: {packages_dir}')
        shutil.copytree(str(package), str(packages_dir / package.name))
        _LOG.info('Copied successfully')

    # copy lambda's handler to artifacts folder
    _LOG.info(f'Copying lambda\'s handler from {root} to {tmp_artifact_path}')
    _copy_py_files(root, tmp_artifact_path)

    # making zip archive
    _LOG.info(f'Packaging artifacts by {tmp_artifact_path} to {package_name}')
    zip_dir(str(tmp_artifact_path), str(Path(artifact_path, package_name)))

    if Path(cache_dir_path, package_name).exists():
        _LOG.info(f"Merging lambda's '{lambda_name}' code with 3-rd party "
                  f"dependencies")
        merge_zip_files(str(Path(artifact_path, package_name)),
                        str(Path(cache_dir_path, package_name)),
                        str(Path(target_folder, package_name)))
    else:
        _LOG.info('Copying lambda\'s code to target folder')
        shutil.copy2(str(Path(artifact_path, package_name)),
                     str(Path(target_folder, package_name)))

    _LOG.info(f'Package \'{package_name}\' was successfully created')

    # remove unused folder
    remove_dir(artifact_path)
    _LOG.info(f'"{artifact_path}" was removed successfully')


def install_requirements_to(requirements_txt: Union[str, Path],
                            to: Union[str, Path],
                            config: Optional[dict] = None,
                            errors_allowed: bool = False):
    """
    1. If there is NO "platform" parameter in lambda_config.json, then the
    dependency installation will be executed by the default command:
    "pip install -r requirements.txt".

    2. If there is NO "platform" parameter in lambda_config.json and flag
    --errors_allowed is True, dependency installation will be tried by
    executing the default command: "pip install -r requirements.txt" in case
    of failures, installation of dependencies will be performed separately
    for each dependency using the default command:
    "pip install <package1>
    pip install <packageN>".

    3. If there is "platform" parameter in lambda_config.json and flag
    --errors_allowed is False, then the dependency installation will be
    executed by the default command using additional parameters:
    "pip install -r requirements.txt --platform manylinux2014_x86_64
    --only-binary=:all: --implementation=cp --python-version 3.8".

    4. If there is "platform" parameter in lambda_config.json and flag
    --errors_allowed is True, dependency installation will be tried by the
    default command using additional parameters:
    "pip install -r requirements.txt --platform manylinux2014_x86_64
    --only-binary=:all: --implementation=cp --python-version 3.8",
    in case of failures, installation of dependencies will be performed
    separately for each dependency using the default command using additional
    parameters. Dependencies that do not have a specified platform will be
    installed with the --platform=any:
    "pip install <package1> --platform manylinux2014_x86_64
    --only-binary=:all: --implementation=cp --python-version 3.8
    pip install <packageN> --platform manylinux2014_x86_64
    --only-binary=:all: --implementation=cp --python-version 3.8
    pip install <packageN+1>".
    """

    exit_code = None
    config = config or {}
    _LOG.info('Going to install 3-rd party dependencies')
    if platforms := config.get('platforms', []):
        if isinstance(platforms, str):
            platforms = [platforms]
        if not isinstance(platforms, list):
            raise InvalidTypeError(
                'Lambda function parameter \'platforms\' must be type of list')
    supported_platforms = update_platforms(set(platforms))
    python_version = _get_python_version(lambda_config=config)
    if supported_platforms:
        command = build_pip_install_command(  # default installation
            requirement=requirements_txt,
            to=to,
            platforms=supported_platforms,
            python=python_version,
            only_binary=':all:',
            implementation='cp'
        )
        result = subprocess.run(command, capture_output=True, text=True)
        _LOG.info(f'\n{result.stdout}\n{result.stderr}')
        if result.returncode != 0 and errors_allowed:
            # tries to install packages compatible with specific platforms
            # independently
            _LOG.info(
                f'Going to install 3-rd party dependencies for platforms: '
                f'{",".join(supported_platforms)}')
            failed_requirements = install_requirements_independently(
                requirements=requirements_txt,
                to=to,
                supported_platforms=supported_platforms,
                python_version=python_version
            )
            failed_requirements = install_requirements_independently(
                requirements=failed_requirements,
                to=to
            )

            _LOG.info(f'\n{result.stdout}\n{result.stderr}')
            if failed_requirements:
                message = (f'An error occurred while installing '
                           f'requirements: "{failed_requirements}" for '
                           f'package "{to}"')
                _LOG.error(message)
                raise ArtifactAssemblingError(message)
        elif result.returncode != 0:
            exit_code = result.returncode
    else:
        _LOG.info('Installing all the requirements with defaults')
        command = build_pip_install_command(
            requirement=requirements_txt,
            to=to
        )
        result = subprocess.run(command, capture_output=True, text=True)
        exit_code = result.returncode

        if result.returncode != 0 and errors_allowed:
            # tries to install packages independently
            _LOG.info(
                'Installing the requirements with defaults independently')
            failed_requirements = install_requirements_independently(
                requirements=requirements_txt,
                to=to
            )

            _LOG.info(f'\n{result.stdout}\n{result.stderr}')
            if failed_requirements:
                message = (f'An error occurred while installing '
                           f'requirements: "{failed_requirements}" for '
                           f'package "{to}"')
                _LOG.error(message)
                raise ArtifactAssemblingError(message)

    if exit_code:
        message = (f'An error: \n"{result.stdout}\n{result.stderr}"\noccurred '
                   f'while installing requirements: "{str(requirements_txt)}" '
                   f'for package "{to}"\nUse --errors-allowed flag to ignore '
                   f'failures in dependencies installation.')
        _LOG.error(message)
        raise ArtifactAssemblingError(message)
    if exit_code == 0:
        _LOG.info(f'\n{result.stdout}\n{result.stderr}')
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


def install_requirements_independently(requirements: Union[str, Path, List[str]],
                                       to: Union[str, Path],
                                       python_version: str = None,
                                       supported_platforms: Set[str] = None) \
        -> List[str]:
    if type(requirements) != list:
        fp = open(requirements, 'r')
        it = (
            line.split(' #')[0].strip() for line in
            filter(lambda line: not line.strip().startswith('#')
                                and line not in EMPTY_LINE_CHARS, fp)
        )
    else:
        it = requirements
    failed_requirements = []
    implementation = 'cp' if python_version or supported_platforms else None
    only_binary = ':all:' if python_version or supported_platforms else None

    for requirement in it:
        command = build_pip_install_command(
            requirement=requirement,
            to=to,
            implementation=implementation,
            python=python_version,
            only_binary=only_binary,
            platforms=supported_platforms
        )
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            message = (f'An error occurred while installing requirements from '
                       f'"{str(requirements)}" for platforms: '
                       f'{",".join(supported_platforms) if supported_platforms else "any"}: '
                       f'for package "{requirement}"'
                       f'\nDetails: \n"{result.stdout}\n{result.stderr}"\n')
            USER_LOG.error(f"\033[93m{message}\033[0m")
            failed_requirements.append(requirement)
        else:
            _LOG.info(f'\n{result.stdout}\n{result.stderr}')
    if type(requirements) != list:
        fp.close()
    return failed_requirements


def _install_local_req(
    artifact_path: str,
    local_req_path: str,
    runtime_root_dir: str
) -> None:
    from syndicate.core import CONFIG

    with open(local_req_path) as f:
        local_req_list = f.readlines()
    local_req_list = [path_resolver(r.strip()) for r in local_req_list]
    _LOG.info(f'Installing local dependencies: {local_req_list}')

    if runtime_root_dir != PYTHON_ROOT_DIR_SRC:
        runtime_abs_path = build_path(
            CONFIG.project_path, runtime_root_dir, PYTHON_ROOT_DIR_SRC
        )
    else:
        runtime_abs_path = build_path(CONFIG.project_path, runtime_root_dir)

    # copy folders
    for lrp in local_req_list:
        _LOG.info(f'Processing local dependency: {lrp}')
        shutil.copytree(
            Path(runtime_abs_path, lrp),
            Path(artifact_path, lrp),
        )
        _LOG.debug('Dependency was copied successfully')

        folders = [r for r in lrp.split(DEFAULT_SEP) if r]
        # process folder from root python project
        folders.insert(0, '')
        i = 0
        temp_path = ''
        while i < len(folders):
            temp_path += DEFAULT_SEP + folders[i]
            src_path = Path(CONFIG.project_path, runtime_root_dir, temp_path)
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
