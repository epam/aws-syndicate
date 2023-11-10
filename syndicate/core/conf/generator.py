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
from botocore.exceptions import ClientError
from boto3.session import Session

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.sts_connection import STSConnection
from syndicate.core.conf.processor import (PROJECT_PATH_CFG,
                                           CONFIG_FILE_NAME,
                                           ALIASES_FILE_NAME,
                                           ACCOUNT_ID_CFG, REGION_CFG,
                                           DEPLOY_TARGET_BUCKET_CFG,
                                           AWS_ACCESS_KEY_ID_CFG,
                                           AWS_SECRET_ACCESS_KEY_CFG,
                                           RESOURCES_PREFIX_CFG,
                                           RESOURCES_SUFFIX_CFG,
                                           TAGS_CFG,
                                           IAM_PERMISSIONS_BOUNDARY_CFG)
from syndicate.core.conf.validator import (LAMBDAS_ALIASES_NAME_CFG,
                                           USE_TEMP_CREDS_CFG,
                                           SERIAL_NUMBER_CFG,
                                           ACCESS_ROLE_CFG,
                                           EXTENDED_PREFIX_MODE_CFG)
from syndicate.core.generators import _mkdir

_LOG = get_logger('config_generator')
_USER_LOG = get_user_logger()


def generate_configuration_files(name, config_path, region,
                                 access_key, secret_key,
                                 bundle_bucket_name, prefix, suffix,
                                 extended_prefix, project_path=None,
                                 use_temp_creds=None, access_role=None,
                                 serial_number=None, tags=None,
                                 iam_permissions_boundary=None):
    if not access_key and not secret_key:
        _USER_LOG.warn("Access_key and secret_key weren't passed. "
                       "Attempting to load them")
        credentials = Session().get_credentials()
        if not credentials:
            raise AssertionError("No credentials could be found")

    try:
        sts = STSConnection(region=region,
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key)
        caller_identity = sts.get_caller_identity()
        account_id = str(caller_identity['Account'])
    except ClientError:
        _USER_LOG.error('Invalid credentials provided, please '
                        'specify the correct one')
        _LOG.exception('Error while account_id obtaining')
        sys.exit(1)

    if not config_path:
        _LOG.warn(f'The config_path property is not specified. '
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

    config_folder_path = os.path.join(config_path, f'.syndicate-config-{name}')
    _mkdir(path=config_folder_path)

    if not project_path:
        _USER_LOG.warn(f'The "{PROJECT_PATH_CFG}" property is not specified. '
                       f'The working directory will be used as a project path.'
                       f' To change the path, edit the {CONFIG_FILE_NAME} '
                       f'by path {config_folder_path}')
        project_path = os.getcwd()
    else:
        if not os.path.exists(project_path):
            raise AssertionError(
                f'Provided project path {project_path} does not exists')
        project_path = os.path.abspath(project_path)

    if use_temp_creds and access_role:
        raise AssertionError(f'Access role mustn\'t be specified if '
                             f'\'use_temp_creds\' parameter is equal to True')

    config_content = {
        ACCOUNT_ID_CFG: account_id,
        REGION_CFG: region,
        DEPLOY_TARGET_BUCKET_CFG: bundle_bucket_name,
        AWS_ACCESS_KEY_ID_CFG: access_key,
        AWS_SECRET_ACCESS_KEY_CFG: secret_key,
        PROJECT_PATH_CFG: project_path,
        RESOURCES_PREFIX_CFG: prefix,
        RESOURCES_SUFFIX_CFG: suffix,
        EXTENDED_PREFIX_MODE_CFG: extended_prefix,
        USE_TEMP_CREDS_CFG: use_temp_creds,
        ACCESS_ROLE_CFG: access_role,
        SERIAL_NUMBER_CFG: serial_number,
        TAGS_CFG: tags,
        IAM_PERMISSIONS_BOUNDARY_CFG: iam_permissions_boundary
    }
    config_content = {key: value for key, value in config_content.items()
                      if value is not None}

    config_file_path = os.path.join(config_folder_path, CONFIG_FILE_NAME)
    with open(config_file_path, 'w') as config_file:
        yaml.dump(config_content, config_file)

    aliases_content = {
        ACCOUNT_ID_CFG: account_id,
        REGION_CFG: region,
        LAMBDAS_ALIASES_NAME_CFG: 'prod',
    }
    aliases_file_path = os.path.join(config_folder_path, ALIASES_FILE_NAME)
    with open(aliases_file_path, 'w') as aliases_file:
        yaml.dump(aliases_content, aliases_file)

    _USER_LOG.info(
        'Syndicate initialization has been completed. \n'
        f'Set SDCT_CONF:{os.linesep}'
        f'Unix: export SDCT_CONF={config_folder_path}{os.linesep}'
        f'Windows: setx SDCT_CONF {config_folder_path}')


def generate_build_project_mapping(mapping_item, build_type):
    type_mapping = ''
    for item in mapping_item:
        type_mapping += f'{build_type}:{item}'
    return type_mapping
