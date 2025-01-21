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

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import run_external_command
from syndicate.core.constants import MVN_TARGET_DIR_NAME
from syndicate.core.helper import build_path, execute_command_by_path, USER_LOG

_LOG = get_logger(__name__)

VALID_EXTENSIONS = ('.jar', '.war', '.zip')
CHECK_MAVEN_INSTALLED_COMMAND = ['mvn', '-version']


def assemble_java_mvn_lambdas(project_path: str, bundles_dir: str,
                              errors_allowed: bool = False,
                              skip_tests: bool = False, **kwargs):
    from syndicate.core import CONFIG

    _check_maven_is_installed()
    target_path = os.path.join(CONFIG.project_path, MVN_TARGET_DIR_NAME)
    src_path = build_path(CONFIG.project_path, project_path)
    _LOG.info(f'Java sources are located by path: {src_path}')
    _LOG.info(f'Going to process java mvn project by path: '
              f'{CONFIG.project_path}')
    command = [shutil.which('mvn'), 'clean', 'install']

    if skip_tests:
        command.append('-DskipTests')

    if errors_allowed:
        command.append('-DerrorsAllowed')

    execute_command_by_path(
        command=command, path=CONFIG.project_path, shell=False)

    # copy java artifacts to the target folder
    for root, dirs, files in os.walk(target_path):
        for file in _filter_bundle_files(files):
            shutil.copyfile(build_path(root, file),
                            build_path(bundles_dir, file))
    _LOG.info('Java mvn project was processed successfully')


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


def _check_maven_is_installed():
    try:
        exit_code, _, _ = run_external_command(CHECK_MAVEN_INSTALLED_COMMAND)
    except Exception:
        USER_LOG.error(
            'It seems like the Maven is not installed. There is no '
            'ability to build a Java bundle. Please, make sure Maven '
            'is installed and retry to build a bundle.')
        raise
