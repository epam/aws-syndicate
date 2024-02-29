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

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import build_path

FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'
INDEX_FILE_NAME = 'index.html'

_LOG = get_logger('syndicate.core.generators.swagger_ui')


def assemble_swagger_ui(project_path, bundles_dir):
    from syndicate.core import CONFIG
    src_path = build_path(CONFIG.project_path, project_path)
    _LOG.info(f'Swagger UI sources are located by path: {src_path}')

    for root, dirs, files in os.walk(src_path):
        for item in dirs:
            _LOG.info(f'Going to process Swagger UI \'{item}\'')

            conf_file_path = build_path(src_path, item,
                                        FILE_DEPLOYMENT_RESOURCES)
            if not os.path.isfile(conf_file_path):
                raise AssertionError(
                    f'\'{FILE_DEPLOYMENT_RESOURCES}\' file not found for '
                    f'Swagger UI \'{item}\'.')

            index_file_path = build_path(src_path, item,
                                         INDEX_FILE_NAME)
            if not os.path.isfile(index_file_path):
                raise AssertionError(
                    f'\'{index_file_path}\' file not found for '
                    f'Swagger UI \'{item}\'.')

            with open(conf_file_path) as file:
                swagger_conf = json.load(file)
            spec_path = swagger_conf[item].get('path_to_spec') \
                if swagger_conf.get(item) else None
            if not os.path.isfile(str(spec_path)):
                raise AssertionError(
                    f'Specification file not found for Swagger UI '
                    f'\'{item}\' in specified path {spec_path}.')

            zip_file_path = build_path(src_path, item, f'{item}.zip')
            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                zipf.write(index_file_path)
                zipf.write(spec_path)
            shutil.move(zip_file_path, build_path(bundles_dir,
                                                  f'{item}.zip'))

            _LOG.info(f'Swagger UI {item} was processed successfully')
