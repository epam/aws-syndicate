"""
    Copyright 2024 EPAM Systems, Inc.

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
import sys
from pathlib import Path, PurePath

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core import ProjectState, CONF_PATH
from syndicate.core.constants import APPSYNC_SCHEMA_DEFAULT_FILE_NAME, \
    APPSYNC_CONFIG_FILE_NAME
from syndicate.core.generators import _mkdir, _touch, _write_content_to_file
from syndicate.core.generators.contents import _generate_syncapp_config, \
    _generate_syncapp_default_schema
from syndicate.core.groups import RUNTIME_APPSYNC
from syndicate.core.project_state.project_state import BUILD_MAPPINGS


APPSYNC_FILES = [APPSYNC_SCHEMA_DEFAULT_FILE_NAME, APPSYNC_CONFIG_FILE_NAME]


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def generate_appsync(name, project_path, tags):
    path_to_project = Path(project_path)

    if not Path.exists(path_to_project):
        USER_LOG.info(f'Project "{project_path}" you '
                      f'have provided does not exist')
        return
    if not ProjectState.check_if_project_state_exists(CONF_PATH):
        USER_LOG.info(f'State file does not exist in {CONF_PATH}')
        return

    project_state = ProjectState(project_path=project_path)
    appsync_abs_path = PurePath(
        project_path, BUILD_MAPPINGS[RUNTIME_APPSYNC], name
    ).as_posix()
    if Path(appsync_abs_path).exists():
        answer = _mkdir(
            path=appsync_abs_path,
            fault_message=f'AppSync API with name \'{name}\' already exists.'
                          f'\nOverride? [y/n]')
        if not answer:
            USER_LOG.info(f'Creation of AppSync API \'{name}\' cancelled')
            sys.exit()
    else:
        _mkdir(appsync_abs_path)

    default_schema_content = _generate_syncapp_default_schema()
    config_content = _generate_syncapp_config(
        name, APPSYNC_SCHEMA_DEFAULT_FILE_NAME, tags)

    for file_name in APPSYNC_FILES:
        path_to_file = PurePath(appsync_abs_path, file_name).as_posix()
        _touch(path_to_file)

        if file_name == APPSYNC_SCHEMA_DEFAULT_FILE_NAME:
            _write_content_to_file(path_to_file, default_schema_content)

        if file_name == APPSYNC_CONFIG_FILE_NAME:
            _write_content_to_file(path_to_file, config_content)

    project_state.add_project_build_mapping(runtime=RUNTIME_APPSYNC)
    project_state.save()
    USER_LOG.info(f'AppSync API \'{name}\' added to the project')
