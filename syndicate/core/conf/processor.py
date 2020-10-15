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

import yaml
from configobj import ConfigObj
from validate import Validator, VdtTypeError

from syndicate.commons.log_helper import get_logger
from syndicate.core.conf.validator import (PROJECT_PATH_CFG, REGION_CFG,
                                           DEPLOY_TARGET_BUCKET_CFG,
                                           ACCOUNT_ID_CFG,
                                           PROJECTS_MAPPING_CFG,
                                           AWS_ACCESS_KEY_ID_CFG,
                                           RESOURCES_PREFIX_CFG,
                                           RESOURCES_SUFFIX_CFG,
                                           AWS_SECRET_ACCESS_KEY_CFG,
                                           ALL_REGIONS, ALLOWED_BUILD_TOOLS,
                                           ConfigValidator)
from syndicate.core.constants import (DEFAULT_SEP, IAM_POLICY, IAM_ROLE,
                                      S3_BUCKET_TYPE)

CONFIG_FILE_NAME = 'syndicate.yml'
ALIASES_FILE_NAME = 'syndicate_aliases.yml'

LEGACY_CONFIG_FILE_NAME = 'sdct.conf'
LEGACY_ALIASES_FILE_NAME = 'sdct_aliases.conf'
DEFAULT_SECTION_NAME = 'default'

_LOG = get_logger('core.conf.config_holder')

GLOBAL_AWS_SERVICES = {IAM_ROLE, IAM_POLICY, S3_BUCKET_TYPE}

REQUIRED_PARAMETERS = {
    PROJECT_PATH_CFG: 'string(min=1)',
    REGION_CFG: "region_func",
    DEPLOY_TARGET_BUCKET_CFG: 'string(min=3, max=63)',
    ACCOUNT_ID_CFG: 'account_func',
    PROJECTS_MAPPING_CFG: 'project_func'
}

ALL_CONFIG_PARAMETERS = [
    AWS_ACCESS_KEY_ID_CFG, AWS_SECRET_ACCESS_KEY_CFG,
    RESOURCES_PREFIX_CFG, RESOURCES_SUFFIX_CFG
]
ALL_CONFIG_PARAMETERS.extend(REQUIRED_PARAMETERS.keys())

ERROR_MESSAGE_MAPPING = {
    PROJECT_PATH_CFG: 'cannot be empty',
    REGION_CFG: "is invalid. Valid options: " + str(ALL_REGIONS),
    DEPLOY_TARGET_BUCKET_CFG: 'length must be between 3 and 63 characters',
    ACCOUNT_ID_CFG: 'must be 12-digit number',
    PROJECTS_MAPPING_CFG: "must be as a mapping of build tool to project "
                          "path, separated by ';'. Build tool name "
                          "and project path should be separated by ':'."
                          " Allowed build "
                          "tools values: " + str(ALLOWED_BUILD_TOOLS),
    RESOURCES_PREFIX_CFG: 'length must be less than or equal to 5',
    RESOURCES_SUFFIX_CFG: 'length must be less than or equal to 5'
}


def _region(value):
    value = value.lower()
    if not isinstance(value, str):
        raise VdtTypeError(value)
    if value not in ALL_REGIONS:
        raise VdtTypeError(value)
    return value


def _account(value):
    if len(value) != 12:
        raise VdtTypeError(value)
    try:
        int(value)
    except:
        raise VdtTypeError(value)
    return value


def _project_mapping(value):
    if value is '' or None:
        return ''  # valid case if you have no projects to build
    mappings = value.split(';')
    for mapping in mappings:
        items = mapping.split(':')
        if len(items) != 2:
            raise VdtTypeError(value)
        if items[0] not in ALLOWED_BUILD_TOOLS:
            raise VdtTypeError(value)
    return value


class ConfigHolder:
    def __init__(self, dir_path):
        con_path = os.path.join(dir_path, CONFIG_FILE_NAME)
        if os.path.isfile(con_path):
            self._init_yaml_config(dir_path=dir_path, con_path=con_path)
        else:
            self._init_ini_config(dir_path=dir_path)

    def _init_yaml_config(self, dir_path, con_path):
        config_content = load_yaml_file_content(file_path=con_path)
        if config_content:
            validator = ConfigValidator(config_content)
            errors = validator.validate()
            if errors:
                raise AssertionError(f'The following error occurred '
                                     f'while {con_path} parsing: {errors}')
        self._config_dict = config_content

        aliases_path = os.path.join(dir_path, ALIASES_FILE_NAME)
        aliases_content = load_yaml_file_content(file_path=aliases_path)
        self._aliases = aliases_content

    def _init_ini_config(self, dir_path):
        con_path = os.path.join(dir_path, LEGACY_CONFIG_FILE_NAME)
        if not os.path.isfile(con_path):
            raise AssertionError(
                'sdct.conf does not exist inside %s folder' % dir_path)
        self._config_path = con_path
        self._config_dict = ConfigObj(con_path,
                                      configspec=REQUIRED_PARAMETERS)
        self._validate_ini()
        alias_path = os.path.join(dir_path, LEGACY_ALIASES_FILE_NAME)
        if not os.path.exists(alias_path):
            _LOG.warn('sdct_aliases.conf does not exist '
                      'inside %s folder' % dir_path)
        else:
            self._aliases = ConfigObj(alias_path)

    def _validate_ini(self):
        # building a validator
        validator = Validator({
            'region_func': _region,
            'account_func': _account,
            'project_func': _project_mapping
        })
        # validate
        param_valid_dict = self._config_dict.validate(validator=validator)
        if not param_valid_dict:
            raise Exception(f'Error while parsing {self._config_path}')
        # check non-required parameters
        prefix_value = self._config_dict.get(RESOURCES_PREFIX_CFG)
        if prefix_value:
            if len(prefix_value) > 5:
                if not isinstance(param_valid_dict, dict):
                    param_valid_dict = {RESOURCES_PREFIX_CFG: False}
                else:
                    param_valid_dict[RESOURCES_PREFIX_CFG] = False

        suffix_value = self._config_dict.get(RESOURCES_SUFFIX_CFG)
        if suffix_value:
            if len(suffix_value) > 5:
                if not isinstance(param_valid_dict, dict):
                    param_valid_dict = {RESOURCES_SUFFIX_CFG: False}
                else:
                    param_valid_dict[RESOURCES_SUFFIX_CFG] = False

        # processing results
        if isinstance(param_valid_dict, dict):
            messages = ''
            for key, value in param_valid_dict.items():
                if not value:
                    messages += '\n{0} {1}'.format(key,
                                                   ERROR_MESSAGE_MAPPING[key])

            if messages:
                raise Exception('Configuration is invalid. ' + messages)

    def _resolve_variable(self, variable_name):
        return self._config_dict.get(variable_name)

    @property
    def project_path(self):
        return path_resolver(self._resolve_variable(PROJECT_PATH_CFG))

    @property
    def account_id(self):
        return str(self._resolve_variable(ACCOUNT_ID_CFG))

    @property
    def access_role(self):
        return self._resolve_variable('access_role')

    @property
    def session_duration(self):
        duration = self._resolve_variable('session_duration')
        if duration:
            return int(self._resolve_variable('session_duration'))

    @property
    def aws_access_key_id(self):
        return self._resolve_variable(AWS_ACCESS_KEY_ID_CFG)

    @property
    def aws_secret_access_key(self):
        return self._resolve_variable(AWS_SECRET_ACCESS_KEY_CFG)

    @property
    def region(self):
        return self._resolve_variable(REGION_CFG)

    @property
    def deploy_target_bucket(self):
        return self._resolve_variable(DEPLOY_TARGET_BUCKET_CFG)

    # mapping build tool : paths to project
    @property
    def build_projects_mapping(self):
        mapping_value = self._resolve_variable(PROJECTS_MAPPING_CFG)
        if type(mapping_value) == dict:
            return mapping_value
        if mapping_value:
            mapping_dict = {}
            for i in mapping_value.split(';'):
                key = i.split(':')[0]
                value = i.split(':')[1]
                list_values = mapping_dict.get(key)
                if list_values:
                    list_values.append(path_resolver(value))
                else:
                    mapping_dict[key] = [path_resolver(value)]
            return mapping_dict

    @property
    def resources_prefix(self):
        prefix = self._resolve_variable(RESOURCES_PREFIX_CFG)
        if prefix is None:
            return ''
        else:
            return prefix

    @property
    def resources_suffix(self):
        suffix = self._resolve_variable(RESOURCES_SUFFIX_CFG)
        if suffix is None:
            return ''
        else:
            return suffix

    @property
    def iam_suffix(self):
        """
        Optional property. It will be included as a ending
        of names for iam_roles.
        :return:
        """
        return self._resolve_variable('iam_suffix')

    @property
    def aliases(self):
        return self._aliases

    def resolve_alias(self, name):
        if self._aliases.get(name):
            return self._aliases[name]


def path_resolver(path):
    return path.replace('\\', DEFAULT_SEP).replace('//', DEFAULT_SEP)


def load_yaml_file_content(file_path):
    if not os.path.isfile(file_path):
        raise AssertionError(f'There is no file by path: {file_path}')
    with open(file_path, 'r') as yaml_file:
        return yaml.load(yaml_file, Loader=yaml.FullLoader)
