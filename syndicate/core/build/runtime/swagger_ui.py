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
import json
import os
import shutil
import zipfile

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import SWAGGER_UI_SPEC_NAME_TEMPLATE, \
    SWAGGER_UI_ARTIFACT_NAME_TEMPLATE, SWAGGER_UI_CONFIG_FILE_NAME
from syndicate.core.helper import build_path

FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
INDEX_FILE_NAME = 'index.html'

_LOG = get_logger('syndicate.core.generators.swagger_ui')
USER_LOG = get_user_logger()


def assemble_swagger_ui(project_path, bundles_dir):
    from syndicate.core import CONFIG
    path_to_project = CONFIG.project_path
    src_path = build_path(path_to_project, project_path)
    _LOG.info(f'Swagger UI sources are located by path: {src_path}')

    for root, dirs, files in os.walk(src_path):
        for item in dirs:
            _LOG.info(f'Going to process Swagger UI \'{item}\'')

            conf_file_path = build_path(src_path, item,
                                        SWAGGER_UI_CONFIG_FILE_NAME)
            if not os.path.isfile(conf_file_path):
                raise AssertionError(
                    f'\'{SWAGGER_UI_CONFIG_FILE_NAME}\' file not found for '
                    f'Swagger UI \'{item}\'.')

            index_file_path = build_path(src_path, item,
                                         INDEX_FILE_NAME)
            if not os.path.isfile(index_file_path):
                raise AssertionError(
                    f'\'{index_file_path}\' file not found for '
                    f'Swagger UI \'{item}\'.')

            with open(conf_file_path) as file:
                swagger_conf = json.load(file)
            spec_path = swagger_conf.get('path_to_spec') \
                if swagger_conf.get('path_to_spec') else ''
            if not os.path.isabs(spec_path):
                spec_path = build_path(path_to_project, spec_path)
                USER_LOG.info(f'Path to specification file resolved as '
                              f'\'{spec_path}\'')
            if not os.path.isfile(spec_path):
                raise AssertionError(
                    f'Specification file not found for Swagger UI '
                    f'\'{item}\' in the path {spec_path}.')

            artifact_name = SWAGGER_UI_ARTIFACT_NAME_TEMPLATE.format(name=item)
            spec_name = SWAGGER_UI_SPEC_NAME_TEMPLATE.format(name=item)
            zip_file_path = build_path(src_path, item, artifact_name)
            swagger_conf['deployment_package'] = artifact_name

            with open(conf_file_path, "w") as file:
                json.dump(swagger_conf, file)

            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                zipf.write(index_file_path, INDEX_FILE_NAME)
                zipf.write(spec_path, spec_name)
            shutil.move(zip_file_path, build_path(bundles_dir,
                                                  artifact_name))

            _LOG.info(f'Swagger UI {item} was processed successfully')
