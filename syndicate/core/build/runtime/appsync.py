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
from syndicate.core.constants import APPSYNC_ARTIFACT_NAME_TEMPLATE, \
    APPSYNC_CONFIG_FILE_NAME, APPSYNC_RESOLVERS_FOLDER, RESOURCES_FILE_NAME
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

    for item in os.listdir(src_path):
        appsync_src_path = build_path(src_path, item)
        if os.path.isdir(appsync_src_path):
            _LOG.info(f'Going to process \'{item}\'')
            if not os.listdir(appsync_src_path):
                raise AssertionError(
                    f'Appsync path {appsync_src_path} is empty')

            conf_file_path = build_path(src_path, item,
                                        APPSYNC_CONFIG_FILE_NAME)
            if not os.path.isfile(conf_file_path):
                raise AssertionError(
                    f'\'{APPSYNC_CONFIG_FILE_NAME}\' file not found for '
                    f'Appsync \'{item}\'.')

            with open(conf_file_path) as file:
                appsync_conf = json.load(file)
            schema_path = appsync_conf.get('schema_path')
            if not os.path.isabs(schema_path):
                schema_path = build_path(appsync_src_path, schema_path)
                USER_LOG.info(f'Path to schema file resolved as '
                              f'\'{schema_path}\'')
            if not os.path.isfile(schema_path):
                raise AssertionError(
                    f'Schema file not found for Appsync \'{item}\' in the '
                    f'path {schema_path}.')

            artifact_name = APPSYNC_ARTIFACT_NAME_TEMPLATE.format(name=item)
            zip_file_path = build_path(src_path, artifact_name)
            appsync_conf['deployment_package'] = artifact_name

            with open(conf_file_path, 'w') as file:
                json.dump(appsync_conf, file)

            resolvers = appsync_conf.get('resolvers')
            resolvers_path = []
            for resolver in resolvers:
                resolvers_path.append(
                    build_path(resolver.get('type_name', '').lower(),
                               resolver.get('field_name', '').lower()))

            appsync_resolvers_path = build_path(
                appsync_src_path, APPSYNC_RESOLVERS_FOLDER)
            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                for file in os.listdir(appsync_src_path):
                    if RESOURCES_FILE_NAME == file:
                        _LOG.debug(f'Skipping {RESOURCES_FILE_NAME} file '
                                   f'in appsync source folder')
                        continue
                    file_path = build_path(appsync_src_path, file)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, file)

                # to archive only resolvers in config
                for path in resolvers_path:
                    resolver_path = build_path(appsync_resolvers_path, path)
                    if os.path.exists(resolver_path) and os.listdir(
                            resolver_path):
                        for root, dirs, files in os.walk(resolver_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                zipf.write(
                                    file_path, build_path(
                                        APPSYNC_RESOLVERS_FOLDER, path, file))

            if os.path.getsize(zip_file_path) == 0:
                raise AssertionError(
                    f'Appsync archive {zip_file_path} is empty')

            shutil.move(zip_file_path, build_path(bundles_dir, artifact_name))
            _LOG.info(f'Appsync {item} was processed successfully')
