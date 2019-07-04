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

from configobj import ConfigObj
from validate import Validator, VdtTypeError

from syndicate.commons.log_helper import get_logger
from syndicate.core.constants import (DEFAULT_SEP, IAM_POLICY, IAM_ROLE,
                                      S3_BUCKET_TYPE)

CONFIG_FILE_NAME = 'sdct.conf'

_LOG = get_logger('core.conf.config_holder')

ALL_REGIONS = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'sa-east-1',
               'ca-central-1', 'eu-west-1', 'eu-central-1', 'eu-west-2',
               'eu-west-3', 'ap-northeast-1', 'ap-northeast-2',
               'ap-southeast-1', 'ap-southeast-2', 'ap-south-1']

GLOBAL_AWS_SERVICES = {IAM_ROLE, IAM_POLICY, S3_BUCKET_TYPE}

PYTHON_BUILD_TOOL_NAME = 'python'
MVN_BUILD_TOOL_NAME = 'mvn'

ALLOWED_BUILDS = [PYTHON_BUILD_TOOL_NAME, MVN_BUILD_TOOL_NAME]

REQUIRED_PARAMETERS = {
    'project_path': 'string(min=1)',
    'region': "region_func",
    'deploy_target_bucket': 'string(min=3, max=63)',
    'account_id': 'account_func',
    'build_projects_mapping': 'project_func'
}

ERROR_MESSAGE_MAPPING = {
    'project_path': 'cannot be empty',
    'region': "is invalid. Valid options: " + str(ALL_REGIONS),
    'deploy_target_bucket': 'length must be between 3 and 63 characters',
    'account_id': 'must be 12-digit number',
    'build_projects_mapping': "must be as a mapping of build tool to project "
                              "path, separated by ';'. Build tool name "
                              "and project path should be separated by ':'."
                              " Allowed build "
                              "tools values: " + str(ALLOWED_BUILDS),
    'resources_prefix': 'length must be less than or equal to 5',
    'resources_suffix': 'length must be less than or equal to 5'
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
        if items[0] not in ALLOWED_BUILDS:
            raise VdtTypeError(value)
    return value


class ConfigHolder:
    def __init__(self, dir_path):
        con_path = os.path.join(dir_path, CONFIG_FILE_NAME)
        if not os.path.isfile(con_path):
            raise Exception(
                'sdct.conf does not exist inside %s folder' % dir_path)
        self._config_dict = ConfigObj(con_path, configspec=REQUIRED_PARAMETERS)
        # validate
        self._validate()
        # load parameters to env vars
        self._load_vars()
        # init aliases
        alias_path = os.path.join(dir_path, 'sdct_aliases.conf')
        if not os.path.exists(alias_path):
            _LOG.warn('sdct_aliases.conf does not exist '
                      'inside %s folder' % dir_path)
        else:
            self._aliases = ConfigObj(alias_path)

    def _validate(self):
        # building a validator
        validator = Validator({
            'region_func': _region,
            'account_func': _account,
            'project_func': _project_mapping
        })
        # validate
        param_valid_dict = self._config_dict.validate(validator=validator)
        # check non-required parameters
        prefix_value = self._config_dict.get('resources_prefix')
        if prefix_value:
            if len(prefix_value) > 5:
                if not isinstance(param_valid_dict, dict):
                    param_valid_dict = {'resources_prefix': False}
                else:
                    param_valid_dict['resources_prefix'] = False

        suffix_value = self._config_dict.get('resources_suffix')
        if suffix_value:
            if len(suffix_value) > 5:
                if not isinstance(param_valid_dict, dict):
                    param_valid_dict = {'resources_suffix': False}
                else:
                    param_valid_dict['resources_suffix'] = False

        # processing results
        if isinstance(param_valid_dict, dict):
            messages = ''
            for key, value in param_valid_dict.items():
                if not value:
                    messages += '\n{0} {1}'.format(key,
                                                   ERROR_MESSAGE_MAPPING[key])

            if messages:
                raise Exception('Configuration is invalid. ' + messages)

    def _load_vars(self):
        for key, value in self._config_dict.items():
            if os.environ.get(key) is None:
                os.environ[key] = value

    def _resolve_variable(self, variable_name):
        var = None
        if self._config_dict.get(variable_name):
            var = self._config_dict[variable_name]
        return var

    @property
    def project_path(self):
        return path_resolver(self._resolve_variable('project_path'))

    @property
    def account_id(self):
        return self._resolve_variable('account_id')

    @property
    def access_role(self):
        return self._resolve_variable('access_role')

    @property
    def aws_access_key_id(self):
        return self._resolve_variable('aws_access_key_id')

    @property
    def aws_secret_access_key(self):
        return self._resolve_variable('aws_secret_access_key')

    @property
    def region(self):
        return self._resolve_variable('region')

    @property
    def deploy_target_bucket(self):
        return self._resolve_variable('deploy_target_bucket')

    # mapping build tool : paths to project
    @property
    def build_projects_mapping(self):
        mapping_value = self._resolve_variable('build_projects_mapping')
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
        prefix = self._resolve_variable('resources_prefix')
        if prefix is None:
            return ''
        else:
            return prefix

    @property
    def resources_suffix(self):
        suffix = self._resolve_variable('resources_suffix')
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
