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
from syndicate.core.helper import build_path, execute_command_by_path

_LOG = get_logger('java_runtime_assembler')

MVN_TARGET_DIRECTORY = 'target'


def assemble_java_mvn_lambdas(project_path, bundles_dir):
    from syndicate.core import CONFIG
    src_path = build_path(CONFIG.project_path, project_path)
    _LOG.info(f'Java sources are located by path: {src_path}')
    _LOG.info(f'Going to process java mvn project by path: '
              f'{CONFIG.project_path}')
    execute_command_by_path(command='mvn clean install',
                            path=CONFIG.project_path)

    # copy java artifacts to the target folder
    for root, dirs, files in os.walk(os.path.join(CONFIG.project_path,
                                                  MVN_TARGET_DIRECTORY)):
        for file in files:
            if file.endswith(".jar") or file.endswith(".war") \
                    or file.endswith(".zip"):
                shutil.copyfile(build_path(root, file),
                                build_path(bundles_dir, file))
    _LOG.info('Java mvn project was processed successfully')
