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
import os
import shutil

from syndicate.exceptions import EnvironmentError
from syndicate.commons.log_helper import get_logger
from syndicate.core.constants import MVN_TARGET_DIR_NAME
from syndicate.core.helper import build_path, execute_command_by_path, USER_LOG
from syndicate.core.groups import JAVA_ROOT_DIR_JAPP

_LOG = get_logger(__name__)

VALID_EXTENSIONS = ('.jar', '.war', '.zip')


def assemble_java_mvn_lambdas(
    runtime_root_dir: str, 
    bundles_dir: str,
    errors_allowed: bool = False,
    skip_tests: bool = False, 
    **kwargs
) -> None:
    from syndicate.core import CONFIG
    project_path = CONFIG.project_path
    mvn_path = safe_resolve_mvn_path()

    mvn_execute_command = [mvn_path, 'clean', 'install']


    if skip_tests:
        mvn_execute_command.append('-DskipTests')

    if errors_allowed:
        mvn_execute_command.append('-DerrorsAllowed')


    if runtime_root_dir == JAVA_ROOT_DIR_JAPP:
        runtime_abs_path = build_path(project_path, JAVA_ROOT_DIR_JAPP)
        _LOG.info(f'Java project are located by path: {runtime_abs_path}')
    else:
        _LOG.warning(
            f"The specified Java root directory '{runtime_root_dir}' is not "
            "standard. Executing Maven commands in the base project directory."
        )
        runtime_abs_path = project_path

    if not os.path.exists(runtime_abs_path):
        error_message = (
            f'Cannot find the Java root directory by path: '
            f'{runtime_abs_path}. Please make sure that the Java project is '
            f'located in the "{runtime_root_dir}" subdirectory.'
        )
        USER_LOG.error(error_message)
        raise EnvironmentError(error_message)
    _LOG.info(
        f"Going to process java mvn project by path: {runtime_abs_path}"
    )
    execute_command_by_path(
        command=mvn_execute_command, path=runtime_abs_path, shell=False
    )

    target_paths = []
    if runtime_root_dir == JAVA_ROOT_DIR_JAPP:
        target_paths = _resolve_all_target_paths(base_path=runtime_abs_path)
    else:
        _LOG.warning(
            f"The specified Java root directory '{runtime_root_dir}' is not "
            "standard. Collecting artifacts from the base project directory."
        )
        target_path = build_path(project_path, MVN_TARGET_DIR_NAME)
        target_paths.append(target_path)
    _LOG.info(f'Java build artifacts are located by paths: {target_paths}')

    for target_path in target_paths:
        _copy_artifacts_from_target_to_bundles_dir(
            target_path=target_path,
            bundles_dir=bundles_dir
        )
    
    _LOG.info('Java mvn project was processed successfully')


def safe_resolve_mvn_path() -> str:
    mvn_path = shutil.which('mvn')
    if not mvn_path:
        error_message = (
            'It seems that Apache Maven is not installed. Therefore, Java '
            'artifacts cannot be assembled. Please make sure that Apache '
            'Maven is installed and retry to build a bundle.'
        )
        USER_LOG.error(error_message)
        raise EnvironmentError(error_message)
    return mvn_path


def _resolve_all_target_paths(base_path: str) -> list[str]:
    target_paths = []
    for root, dirs, _ in os.walk(base_path):
        if MVN_TARGET_DIR_NAME in dirs:
            target_paths.append(build_path(root, MVN_TARGET_DIR_NAME))
    return target_paths


def _copy_artifacts_from_target_to_bundles_dir(
    target_path: str, bundles_dir: str
) -> None:
    for root, _, files in os.walk(target_path):
        for file in _filter_bundle_files(files):
            target_file_path = build_path(root, file)
            bundle_file_path = build_path(bundles_dir, file)
            _LOG.info(f'Copying file {target_file_path} to {bundle_file_path}')

            shutil.copyfile(
                target_file_path,
                bundle_file_path
            )


def _filter_bundle_files(files: list[str]) -> list[str]:
    filtered_files = []
    exclude_prefix = 'original-'

    # to exclude redundant original-<lambda_name>.jar file
    # but do not exclude lambda jar if its name starts with 'original-'
    if sum(1 for item in files if item.startswith('original-')) > 1:
        exclude_prefix = 'original-original-'

    for file in files:
        if file.endswith(VALID_EXTENSIONS) and not \
                (file.startswith(exclude_prefix) and file.endswith('.jar')):
            filtered_files.append(file)
    return filtered_files
