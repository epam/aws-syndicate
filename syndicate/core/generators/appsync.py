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
from syndicate.core import ProjectState
from syndicate.core.generators import _mkdir, _touch, _write_content_to_file
from syndicate.core.generators.contents import _generate_syncapp_dr, \
    _generate_syncapp_default_schema
from syndicate.core.groups import RUNTIME_APPSYNC
from syndicate.core.project_state.project_state import BUILD_MAPPINGS


FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
DEFAULT_SCHEMA_FILE_NAME = 'schema.graphql'
DEFAULT_SCHEMA_PATH = \
    f'{BUILD_MAPPINGS[RUNTIME_APPSYNC]}/$APPSYNC_NAME/{DEFAULT_SCHEMA_FILE_NAME}'


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def generate_appsync(name, project_path, tags, schema_path):
    path_to_project = Path(project_path)
    default_schema_path = True if schema_path == DEFAULT_SCHEMA_FILE_NAME \
        else False
    if not Path.exists(path_to_project):
        USER_LOG.info(f'Project "{project_path}" you '
                      f'have provided does not exist')
        return
    if not ProjectState.check_if_project_state_exists(
            project_path=project_path):
        USER_LOG.info(f'Seems that the path {project_path} is not a project')
        return
    if not default_schema_path:
        abs_path_to_schema = Path(schema_path)
        if not Path.is_absolute(Path(schema_path)):
            abs_path_to_schema = Path.joinpath(path_to_project,
                                               Path(schema_path))
            _LOG.info(f'Path to schema file resolved as '
                      f'\'{abs_path_to_schema}\'')
        if not Path.is_file(abs_path_to_schema):
            raise AssertionError(
                f'Provided schema file \'{schema_path}\' can\'t be '
                f'resolved! Please provide the correct path.')
    # else:
    #     path_to_schema = Path(
    #         DEFAULT_SCHEMA_PATH.replace('$APPSYNC_NAME', name))
    #     abs_path_to_schema = Path.joinpath(path_to_project,
    #                                        Path(path_to_schema))

    project_state = ProjectState(project_path=project_path)
    src_path = PurePath(project_path,
                        BUILD_MAPPINGS[RUNTIME_APPSYNC],
                        name).as_posix()
    answer = _mkdir(path=src_path,
                    fault_message=f'AppSync API with name \'{name}\' already '
                                  f'exists.\nOverride? [y/n]')
    if not answer:
        USER_LOG.info(f'Creation of AppSync API \'{name}\' cancelled')
        sys.exit()

    if default_schema_path:
        schema_path = (f'{BUILD_MAPPINGS[RUNTIME_APPSYNC]}/{name}/'
                       f'{DEFAULT_SCHEMA_FILE_NAME}')
        abs_path_to_schema = Path.joinpath(path_to_project, Path(schema_path))
        _touch(PurePath(abs_path_to_schema).as_posix())
        default_schema_content = _generate_syncapp_default_schema()
        _write_content_to_file(abs_path_to_schema, default_schema_content)

    _touch(PurePath(src_path, FILE_DEPLOYMENT_RESOURCES).as_posix())

    deployment_resources_content = _generate_syncapp_dr(name, schema_path,
                                                        tags)

    _write_content_to_file(
        PurePath(src_path, FILE_DEPLOYMENT_RESOURCES).as_posix(),
        deployment_resources_content)

    project_state.add_project_build_mapping(runtime=RUNTIME_APPSYNC)
    project_state.save()
    USER_LOG.info(f'AppSync API \'{name}\' added to the project')
