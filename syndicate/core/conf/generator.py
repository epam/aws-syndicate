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
import sys

import yaml

from syndicate.commons.log_helper import get_logger
from syndicate.core.conf.processor import (PROJECT_PATH_CFG,
                                           LEGACY_CONFIG_FILE_NAME,
                                           CONFIG_FILE_NAME,
                                           ALIASES_FILE_NAME,
                                           ACCOUNT_ID_CFG, REGION_CFG,
                                           DEPLOY_TARGET_BUCKET_CFG,
                                           AWS_ACCESS_KEY_ID_CFG,
                                           AWS_SECRET_ACCESS_KEY_CFG,
                                           PROJECTS_MAPPING_CFG,
                                           RESOURCES_PREFIX_CFG,
                                           RESOURCES_SUFFIX_CFG)
from syndicate.core.conf.validator import (PYTHON_BUILD_TOOL_NAME,
                                           MVN_BUILD_TOOL_NAME,
                                           NODE_BUILD_TOOL_NAME,
                                           LAMBDAS_ALIASES_NAME_CFG)

_LOG = get_logger('config_generator')


def generate_configuration_files(config_path, region, account_id,
                                 access_key, secret_key,
                                 bundle_bucket_name, python_build_mapping,
                                 java_build_mapping,
                                 nodejs_build_mapping, prefix, suffix,
                                 project_path=None):
    if not config_path:
        _LOG.warn(f'The {config_path} property is not specified. '
                  f'The working directory is used')
        config_path = os.getcwd()

    if not os.path.exists(config_path):
        try:
            os.mkdir(config_path)
        except OSError:
            _LOG.exception(
                f'Error has occurred while creating '
                f'directory for configs {config_path}')
            sys.exit(1)

    if not project_path:
        _LOG.warn(f'The {PROJECT_PATH_CFG} property is not specified. '
                  f'The working directory will be used as a project path. '
                  f'To change the path, edit the {LEGACY_CONFIG_FILE_NAME} '
                  f'by path {config_path}')
        project_path = os.getcwd()
    else:
        if not os.path.exists(project_path):
            raise AssertionError(
                f'Provided project path {project_path} does not exists')

    build_project_mapping = {}
    if python_build_mapping:
        build_project_mapping[PYTHON_BUILD_TOOL_NAME] = \
            list(python_build_mapping)
    if java_build_mapping:
        build_project_mapping[MVN_BUILD_TOOL_NAME] = list(java_build_mapping)
    if nodejs_build_mapping:
        build_project_mapping[NODE_BUILD_TOOL_NAME] = \
            list(nodejs_build_mapping)

    config_content = {
        ACCOUNT_ID_CFG: account_id,
        REGION_CFG: region,
        DEPLOY_TARGET_BUCKET_CFG: bundle_bucket_name,
        AWS_ACCESS_KEY_ID_CFG: access_key,
        AWS_SECRET_ACCESS_KEY_CFG: secret_key,
        PROJECT_PATH_CFG: project_path,
        PROJECTS_MAPPING_CFG: build_project_mapping,
        RESOURCES_PREFIX_CFG: prefix,
        RESOURCES_SUFFIX_CFG: suffix
    }

    config_file_path = f'{config_path}/{CONFIG_FILE_NAME}'
    with open(config_file_path, 'w') as config_file:
        yaml.dump(config_content, config_file)

    aliases_content = {
        ACCOUNT_ID_CFG: account_id,
        REGION_CFG: region,
        LAMBDAS_ALIASES_NAME_CFG: 'prod'
    }
    aliases_file_path = f'{config_path}/{ALIASES_FILE_NAME}'
    with open(aliases_file_path, 'w') as aliases_file:
        yaml.dump(aliases_content, aliases_file)

    _LOG.info(
        'Syndicate initialization has been completed. '
        f'Set SDCT_CONF:\nexport SDCT_CONF={config_path}')


def generate_build_project_mapping(mapping_item, build_type):
    type_mapping = ''
    for item in mapping_item:
        type_mapping += f'{build_type}:{item}'
    return type_mapping
