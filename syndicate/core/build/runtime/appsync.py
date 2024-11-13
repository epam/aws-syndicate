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
import os
import shutil
import zipfile

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.meta_processor import resolve_resource_name
from syndicate.core.constants import APPSYNC_ARTIFACT_NAME_TEMPLATE
from syndicate.core.helper import build_path

FILE_DEPLOYMENT_RESOURCES = 'deployment_resources.json'

_LOG = get_logger('syndicate.core.generators.appsync')
USER_LOG = get_user_logger()


def assemble_appsync(project_path, bundles_dir, **kwargs):
    from syndicate.core import CONFIG
    path_to_project = CONFIG.project_path
    src_path = build_path(path_to_project, project_path)
    if not os.path.exists(src_path):
        raise AssertionError(
            f'Appsync sources are not located by path {src_path}')
    if not os.listdir(src_path):
        raise AssertionError(f'Appsync sources path {src_path} is empty')

    _LOG.info(f'Appsync sources are located by path: {src_path}')

    for root, dirs, files in os.walk(src_path):
        for item in dirs:
            _LOG.info(f'Going to process \'{item}\'')
            appsync_src_path = build_path(src_path, item)
            if not os.listdir(appsync_src_path):
                raise AssertionError(
                    f'Appsync path {appsync_src_path} is empty')

            item_prefix_suffix = resolve_resource_name(
                item, CONFIG.resources_prefix, CONFIG.resources_suffix)
            artifact_name = APPSYNC_ARTIFACT_NAME_TEMPLATE.format(
                name=item_prefix_suffix)
            zip_file_path = build_path(src_path, artifact_name)

            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                for zip_root, zip_dirs, zip_files in os.walk(appsync_src_path):
                    for file in zip_files:
                        file_path = build_path(appsync_src_path, file)
                        zipf.write(file_path, file)

            if os.path.getsize(zip_file_path) == 0:
                raise AssertionError(
                    f'Appsync archive {zip_file_path} is empty')

            shutil.move(zip_file_path, build_path(bundles_dir, artifact_name))
            _LOG.info(f'Appsync {item} was processed successfully')
