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
from syndicate.core.generators.contents import SWAGGER_UI_INDEX_FILE_CONTENT, \
     _generate_swagger_ui_deployment_resources
from syndicate.core.generators.project import FILE_DEPLOYMENT_RESOURCES
from syndicate.core.project_state.project_state import BUILD_MAPPINGS

SWAGGER_UI_RUNTIME = 'swagger_ui'
INDEX_FILE_NAME = 'index.html'

_LOG = get_logger('syndicate.core.generators.swagger_ui')
USER_LOG = get_user_logger()


def generate_swagger_ui(name, spec_path, target_bucket, project_path):
    path_to_project = Path(project_path)
    path_to_spec = Path(spec_path)
    if not Path.exists(path_to_project):
        USER_LOG.info(f'Project "{project_path}" you '
                      f'have provided does not exist')
        return
    if not ProjectState.check_if_project_state_exists(
            project_path=project_path):
        USER_LOG.info(f'Seems that the path {project_path} is not a project')
        return
    if not Path.is_absolute(path_to_spec):
        USER_LOG.info(f'Trying to resolve path to specification file '
                      f'\'{spec_path}\'')
        path_to_spec = Path.joinpath(path_to_project, path_to_spec)
    if not Path.is_file(path_to_spec):
        raise AssertionError(f'Provided specification file \'{spec_path}\' '
                             f'can\'t be resolved! Please provide the correct '
                             f'path.')

    project_state = ProjectState(project_path=project_path)
    src_path = PurePath(project_path,
                        BUILD_MAPPINGS[SWAGGER_UI_RUNTIME],
                        name).as_posix()
    answer = _mkdir(path=src_path,
                    fault_message=f'Swagger UI with name \'{name}\' already '
                                  f'exists.\nOverride? [y/n]')
    if not answer:
        USER_LOG.info(f'Creation of Swagger UI \'{name}\' cancelled')
        sys.exit()

    _create_deployment_resources(src_path=src_path,
                                 resource_name=name,
                                 spec_path=PurePath(path_to_spec).as_posix(),
                                 target_bucket=target_bucket)

    _create_index_file(src_path=src_path,
                       spec_file_name=f'{name}_spec.json')

    USER_LOG.info(f'Swagger UI \'{name}\' resource files saved to '
                  f'\'{src_path}\'')

    project_state.add_project_build_mapping(runtime=SWAGGER_UI_RUNTIME)
    project_state.save()
    _LOG.info(f'Swagger UI \'{name}\' added to the project')


def _create_deployment_resources(src_path, resource_name,
                                 spec_path, target_bucket):
    dr_file = PurePath(src_path, FILE_DEPLOYMENT_RESOURCES)
    _touch(dr_file)
    dr_content = _generate_swagger_ui_deployment_resources(resource_name,
                                                           spec_path,
                                                           target_bucket)
    _write_content_to_file(file=dr_file,
                           content=dr_content)


def _create_index_file(src_path, spec_file_name):
    index_file_path = PurePath(src_path, INDEX_FILE_NAME)
    _touch(index_file_path)
    _write_content_to_file(file=index_file_path,
                           content=SWAGGER_UI_INDEX_FILE_CONTENT.replace(
                               'spec_file_name', spec_file_name))
