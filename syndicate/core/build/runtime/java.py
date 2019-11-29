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
from syndicate.core import CONFIG
from syndicate.core.constants import ARTIFACTS_FOLDER
from syndicate.core.helper import build_path, execute_command_by_path

_LOG = get_logger('java_runtime_assembler')


def assemble_java_mvn_lambdas(bundle_name, project_path):
    src_path = build_path(CONFIG.project_path, project_path)
    _LOG.info(
        'Going to process java mvn project by path: {0}'.format(src_path))
    target_folder = build_path(CONFIG.project_path,
                               ARTIFACTS_FOLDER,
                               bundle_name)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    _LOG.debug('Target directory: {0}'.format(target_folder))
    execute_command_by_path(command='mvn clean install', path=src_path)

    # copy java artifacts to the target folder
    for root, dirs, files in os.walk(src_path):
        for file in files:
            if file.endswith(".jar") or file.endswith(".war") \
                    or file.endswith(".zip"):
                shutil.copyfile(build_path(root, file),
                                build_path(target_folder, file))

    _LOG.info('Java mvn project was processed successfully')
