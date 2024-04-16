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
from configparser import ConfigParser
from datetime import datetime
from typing import Union

import yaml

from syndicate.commons.log_helper import get_logger
from syndicate.core.conf.bucket_view import \
    AbstractBucketView, AbstractViewDigest
from syndicate.core.conf.validator import \
    (PROJECT_PATH_CFG, REGION_CFG, DEPLOY_TARGET_BUCKET_CFG,
     ACCOUNT_ID_CFG, PROJECTS_MAPPING_CFG, AWS_ACCESS_KEY_ID_CFG,
     RESOURCES_PREFIX_CFG, RESOURCES_SUFFIX_CFG, AWS_SECRET_ACCESS_KEY_CFG,
     ConfigValidator, USE_TEMP_CREDS_CFG, SERIAL_NUMBER_CFG,
     TEMP_AWS_ACCESS_KEY_ID_CFG, TEMP_AWS_SECRET_ACCESS_KEY_CFG,
     TEMP_AWS_SESSION_TOKEN_CFG, EXPIRATION_CFG, TAGS_CFG,
     IAM_PERMISSIONS_BOUNDARY_CFG, LAMBDAS_ALIASES_NAME_CFG,
     AWS_SESSION_TOKEN_CFG, EXTENDED_PREFIX_MODE_CFG,
     LOCK_LIFETIME_MINUTES_CFG)
from syndicate.core.constants import (DEFAULT_SEP, IAM_POLICY, IAM_ROLE,
                                      S3_BUCKET_TYPE)

CONFIG_FILE_NAME = 'syndicate.yml'
ALIASES_FILE_NAME = 'syndicate_aliases.yml'

LEGACY_CONFIG_FILE_NAME = 'sdct.conf'
LEGACY_ALIASES_FILE_NAME = 'sdct_aliases.conf'

_LOG = get_logger('core.conf.config_holder')

GLOBAL_AWS_SERVICES = {IAM_ROLE, IAM_POLICY, S3_BUCKET_TYPE}

DEFAULT_LOCK_TIME_IN_MINUTES = 20


class ConfigHolder:
    def __init__(self, dir_path):
        con_path_yml = os.path.join(dir_path, CONFIG_FILE_NAME)
        con_path_yaml = os.path.join(dir_path,
                                     CONFIG_FILE_NAME.replace('yml', 'yaml'))
        con_path = con_path_yml if \
            os.path.exists(con_path_yml) else con_path_yaml
        self._config_path = con_path
        if os.path.isfile(con_path):
            self._init_yaml_config(dir_path=dir_path, con_path=con_path)
        else:
            self._init_conf_config(dir_path=dir_path)

    def _assert_no_errors(self, errors: list):
        if errors:
            raise AssertionError(f'The following error occurred '
                                 f'while {self._config_path} '
                                 f'parsing: {errors}')

    def _init_yaml_config(self, dir_path, con_path):
        config_content = load_yaml_file_content(file_path=con_path)
        if config_content:
            validator = ConfigValidator(config_content)
            errors = validator.validate()
            self._assert_no_errors(errors)

        self._config_dict = config_content

        aliases_path_yml = os.path.join(dir_path, ALIASES_FILE_NAME)
        aliases_path_yaml = os.path.join(
            dir_path, ALIASES_FILE_NAME.replace('yml', 'yaml'))
        aliases_path = aliases_path_yml \
            if os.path.exists(aliases_path_yml) else aliases_path_yaml
        aliases_content = load_yaml_file_content(file_path=aliases_path)
        self._aliases = aliases_content
        self._aliases.update(self.default_aliases)

    def _init_conf_config(self, dir_path):
        con_path = os.path.join(dir_path, LEGACY_CONFIG_FILE_NAME)
        if not os.path.isfile(con_path):
            raise AssertionError(
                'sdct.conf does not exist inside %s folder' % dir_path)

        self._config_path = con_path
        self._config_dict = load_conf_file_content(self._config_path)

        validator = ConfigValidator(self._config_dict)
        errors = validator.validate()
        self._assert_no_errors(errors)

        alias_path = os.path.join(dir_path, LEGACY_ALIASES_FILE_NAME)
        if not os.path.exists(alias_path):
            _LOG.warn('sdct_aliases.conf does not exist '
                      'inside %s folder' % dir_path)

        self._aliases = load_conf_file_content(alias_path)
        self._aliases.update(self.default_aliases)

    def set_temp_credentials_to_config(self, temp_aws_access_key_id,
                                       temp_aws_secret_access_key,
                                       temp_aws_session_token,
                                       expiration):
        content_to_update = {
            TEMP_AWS_ACCESS_KEY_ID_CFG: temp_aws_access_key_id,
            TEMP_AWS_SECRET_ACCESS_KEY_CFG: temp_aws_secret_access_key,
            TEMP_AWS_SESSION_TOKEN_CFG: temp_aws_session_token,
            EXPIRATION_CFG: expiration
        }
        update_file_content(
            file_path=self._config_path,
            content=content_to_update
        )

    def _resolve_variable(self, variable_name):
        return self._config_dict.get(variable_name)

    def _resolve_aliases(self, variable_name):
        return self._aliases.get(variable_name)

    def _prepare_bucket_view(self) -> Union[None, AbstractBucketView]:
        """
        Prepares assigned bucket view instance,
        by providing the raw config payload.
        Under circumstances of an error, deletes the previously installed view,
        which defaults to using the raw format.
        :return: [None, AbstractBucketView]
        """
        view = self.deploy_target_bucket_view
        raw = self._resolve_variable(DEPLOY_TARGET_BUCKET_CFG)
        try:
            view.raw = raw
            _LOG.info(f'Viewing complement, {view.__class__.__name__},'
                      ' has been found, setting up the raw data.')
            return view

        except AttributeError:
            _LOG.warn('No viewing complement has been found.')
        except AbstractBucketView.BucketViewRuntimeError:
            _LOG.warn('Viewing complement set-up has failed.')

        del self.deploy_target_bucket_view
        return None

    def _resolve_bucket_view_attribute(self, attribute_name: str,
                                       default=None):
        """
        Retrieves bucket view value respectively to a provided attribute name.
        """
        if not isinstance(attribute_name, str):
            raise KeyError('Name of an attribute must be a string.')
        view = self.deploy_target_bucket_view
        if view and not view.raw:
            view = self._prepare_bucket_view()
        return getattr(view, attribute_name, default)

    @property
    def default_aliases(self):
        return {
            ACCOUNT_ID_CFG: self.account_id,
            REGION_CFG: self.region
        }

    @property
    def project_path(self):
        return path_resolver(self._resolve_variable(PROJECT_PATH_CFG))

    @property
    def account_id(self):
        return str(self._resolve_variable(ACCOUNT_ID_CFG))

    @property
    def lambdas_alias_name(self):
        return str(self._resolve_aliases(LAMBDAS_ALIASES_NAME_CFG))

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
    def aws_session_token(self):
        return self._resolve_variable(AWS_SESSION_TOKEN_CFG)

    @property
    def aws_secret_access_key(self):
        return self._resolve_variable(AWS_SECRET_ACCESS_KEY_CFG)

    @property
    def region(self):
        return self._resolve_variable(REGION_CFG)

    @property
    def deploy_target_bucket(self) -> str:
        return self._resolve_bucket_view_attribute(
            'name', self._resolve_variable(DEPLOY_TARGET_BUCKET_CFG)
        )

    @property
    def deploy_target_bucket_key_compound(self) -> str:
        return self._resolve_bucket_view_attribute('key', '')

    @property
    def deploy_target_bucket_view(self) -> Union[AbstractBucketView, None]:
        return getattr(self, '_deploy_target_bucket_view', None)

    @deploy_target_bucket_view.setter
    def deploy_target_bucket_view(self, view: AbstractBucketView):
        if not isinstance(view, AbstractBucketView):
            _LOG.error('Bucket view couldn\'t have been set, '
                       'due to improper type.')
        elif not isinstance(view.digest, AbstractViewDigest):
            _LOG.error('Bucket view couldn\'t have been set,'
                       ' due to unassigned digest-parser property.')
        else:
            setattr(self, '_deploy_target_bucket_view', view)

    @deploy_target_bucket_view.deleter
    def deploy_target_bucket_view(self):
        delattr(self, '_deploy_target_bucket_view')

    @property
    def iam_permissions_boundary(self):
        return self._resolve_variable(IAM_PERMISSIONS_BOUNDARY_CFG)

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
    def extended_prefix_mode(self):
        prefix_mode = self._resolve_variable(EXTENDED_PREFIX_MODE_CFG)
        return self._resolve_bool_param(prefix_mode)

    @property
    def aliases(self):
        return self._aliases

    @property
    def use_temp_creds(self):
        var = self._resolve_variable(USE_TEMP_CREDS_CFG)
        return self._resolve_bool_param(var)

    @property
    def serial_number(self):
        return self._resolve_variable(SERIAL_NUMBER_CFG)

    @property
    def temp_aws_access_key_id(self):
        return self._resolve_variable(TEMP_AWS_ACCESS_KEY_ID_CFG)

    @property
    def temp_aws_secret_access_key(self):
        return self._resolve_variable(TEMP_AWS_SECRET_ACCESS_KEY_CFG)

    @property
    def temp_aws_session_token(self):
        return self._resolve_variable(TEMP_AWS_SESSION_TOKEN_CFG)

    @property
    def expiration(self):
        return self._resolve_variable(EXPIRATION_CFG)

    @property
    def tags(self) -> dict:
        tags = self._resolve_variable(TAGS_CFG) or {}
        tags = {k: str(v) for k, v in tags.items()}
        return tags

    @property
    def lock_lifetime_minutes(self) -> int:
        return self._resolve_variable(LOCK_LIFETIME_MINUTES_CFG) or \
            DEFAULT_LOCK_TIME_IN_MINUTES

    def resolve_alias(self, name):
        if self._aliases.get(name):
            return self._aliases[name]

    @staticmethod
    def _resolve_bool_param(parameter):
        if isinstance(parameter, bool):
            return parameter
        elif isinstance(parameter, str):
            return parameter.lower() in ("yes", "true", "t", "1")
        return False


def path_resolver(path):
    return path.replace('\\', DEFAULT_SEP).replace('//', DEFAULT_SEP)


def str_to_bool(val):
    if isinstance(val, str):
        if val.lower() == 'true':
            return True
        elif val.lower() == 'false':
            return False
    return val


def str_to_datetime(val):
    if isinstance(val, str):
        if ' ' in val:
            val = val.replace(' ', 'T')
        return datetime.fromisoformat(val)
    return val


def add_default_section(file_path):
    with open(file_path, 'r+') as f:
        lines = f.readlines()
        lines = [line for line in lines if line.strip() != '']

        first_line = lines[0]
        f.seek(0)
        if '[default]' not in first_line:
            rest_of_file = f.read()
            f.seek(0)
            f.write('[default]\n' + rest_of_file)


def load_yaml_file_content(file_path):
    if not os.path.isfile(file_path):
        raise AssertionError(f'There is no file by path: {file_path}')
    with open(file_path, 'r') as yaml_file:
        return yaml.load(yaml_file, Loader=yaml.FullLoader)


def load_conf_file_content(file_path):
    if not os.path.isfile(file_path):
        raise AssertionError(f'There is no file by path: {file_path}')

    add_default_section(file_path)

    config = ConfigParser()
    config.read(file_path)
    config_dict = {}

    for section in config.sections():
        if section == 'tags':
            config_dict[section] = dict(config[section])
        else:
            section_dict = {
                k: str_to_bool(v) if k != 'expiration' else str_to_datetime(v)
                for k, v in dict(config[section]).items()}
            config_dict.update(section_dict)

    return config_dict


def update_file_content(file_path, content):
    if file_path.endswith('.yaml') or file_path.endswith('.yml'):
        update_yaml_file_content(file_path=file_path, content=content)
    elif file_path.endswith('.conf'):
        update_conf_file_content(file_path=file_path, content=content)


def update_yaml_file_content(file_path, content):
    file_content = load_yaml_file_content(file_path=file_path)
    file_content.update(content)
    with open(file_path, 'w') as yaml_file:
        yaml.dump(file_content, yaml_file, default_flow_style=False)


def update_conf_file_content(file_path, content):
    file_content = load_conf_file_content(file_path)
    file_content.update(content)

    config = ConfigParser()
    for key, val in file_content.items():
        if type(val) is dict:
            config.add_section(key)
            for sub_key, sub_val in val.items():
                config.set(key, sub_key, str(sub_val))
        else:
            if not config.has_section('default'):
                config.add_section('default')
            config.set('default', key, str(val))

    with open(file_path, 'w') as f:
        config.write(f)
