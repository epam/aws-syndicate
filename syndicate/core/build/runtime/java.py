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
from syndicate.core.groups import JAVA_ROOT_DIR, JAVA_ROOT_DIR_OLD

_LOG = get_logger(__name__)

VALID_EXTENSIONS = ('.jar', '.war', '.zip')


def assemble_java_mvn_lambdas(project_path: str, bundles_dir: str,
                              errors_allowed: bool = False,
                              skip_tests: bool = False, **kwargs):
    from syndicate.core import CONFIG
    runtime_root_dir = project_path
    project_path = CONFIG.project_path
    mvn_path = _safe_resolve_mvn_path()
    src_path = build_path(project_path, runtime_root_dir)

    _LOG.info(f'Java project are located by path: {src_path}')

    command = [mvn_path, 'clean', 'install']

    if skip_tests:
        command.append('-DskipTests')

    if errors_allowed:
        command.append('-DerrorsAllowed')

    mvn_execute = _MVN_EXECUTORS.get(runtime_root_dir, None)
    if not mvn_execute:
        USER_LOG.warning(
            f"The specified Java root directory '{runtime_root_dir}' is not "
            "standard. Executing Maven commands in the base project directory."
        )
        mvn_execute = _MVN_EXECUTORS[JAVA_ROOT_DIR_OLD]

    mvn_execute(mvn_command=command, project_path=project_path)


    collect_artifacts = _ARTIFACT_COLLECTORS.get(runtime_root_dir, None)
    if not collect_artifacts:
        USER_LOG.warning(
            f"The specified Java root directory '{runtime_root_dir}' is not "
            "standard. Collecting artifacts from the base project directory."
        )
        collect_artifacts = _ARTIFACT_COLLECTORS[JAVA_ROOT_DIR_OLD]

    collect_artifacts(
        project_path=project_path,
        runtime_root_dir=runtime_root_dir,
        bundle_dir=bundles_dir
    )
    _LOG.info('Java mvn project was processed successfully')


def _mvn_execute_in_project_root(mvn_command, project_path: str):
    _LOG.info(f"Going to process java mvn project by path: {project_path}")
    return execute_command_by_path(
        command=mvn_command, path=project_path, shell=False
    )


def _mvn_execute_in_runtime_root(mvn_command, project_path: str):
    runtime_root_path = build_path(project_path, JAVA_ROOT_DIR)
    if not os.path.exists(runtime_root_path):
        error_message = (
            f'Cannot find the Java root directory by path: '
            f'{runtime_root_path}. Please make sure that the Java project is '
            f'located in the "{JAVA_ROOT_DIR}" subdirectory.'
        )
        USER_LOG.error(error_message)
        raise EnvironmentError(error_message)
    _LOG.info(
        f"Going to process java mvn project by path: {runtime_root_path}"
    )
    return execute_command_by_path(
        command=mvn_command, path=runtime_root_path, shell=False
    )


def _collect_artifacts_to_bundle_in_project_root(
    project_path: str, runtime_root_dir: str, bundle_dir: str
):
    target_path = build_path(project_path, MVN_TARGET_DIR_NAME)
    _LOG.info(f'Java build artifacts are located by path: {target_path}')
    _copy_artifacts_from_target_to_bundle(
        target_path=target_path,
        bundle_dir=bundle_dir
    )


def _collect_artifacts_to_bundle_in_runtime_root(
    project_path: str, runtime_root_dir: str, bundle_dir: str
):
    runtime_root_path = build_path(project_path, runtime_root_dir)
    target_paths = _resolve_all_target_paths(base_path=runtime_root_path)
    _LOG.info(f'Java build artifacts are located by paths: {target_paths}')
    for target_path in target_paths:
        _copy_artifacts_from_target_to_bundle(
            target_path=target_path,
            bundle_dir=bundle_dir
        )


_MVN_EXECUTORS = {
    JAVA_ROOT_DIR_OLD: _mvn_execute_in_project_root,
    JAVA_ROOT_DIR: _mvn_execute_in_runtime_root
}


_ARTIFACT_COLLECTORS = {
    JAVA_ROOT_DIR_OLD: _collect_artifacts_to_bundle_in_project_root,
    JAVA_ROOT_DIR: _collect_artifacts_to_bundle_in_runtime_root
}



def _resolve_all_target_paths(base_path: str) -> list[str]:
    target_paths = []
    for root, dirs, _ in os.walk(base_path):
        if MVN_TARGET_DIR_NAME in dirs:
            target_paths.append(build_path(root, MVN_TARGET_DIR_NAME))
    return target_paths


def _copy_artifacts_from_target_to_bundle(
    target_path: str, bundle_dir: str
) -> None:
    for root, _, files in os.walk(target_path):
        for file in _filter_bundle_files(files):
            target_file_path = build_path(root, file)
            bundle_file_path = build_path(bundle_dir, file)
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


def _safe_resolve_mvn_path() -> str:
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