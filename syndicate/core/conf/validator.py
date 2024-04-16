"""
    Copyright 2020 EPAM Systems, Inc.

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
import datetime
import os
import re
from syndicate.core.conf.bucket_view import NAMED_S3_URI_PATTERN
from syndicate.commons.log_helper import get_user_logger

MIN_BUCKET_NAME_LEN = 3
MAX_BUCKET_NAME_LEN = 63

ALL_REGIONS = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'sa-east-1',
               'ca-central-1', 'eu-west-1', 'eu-central-1', 'eu-west-2',
               'eu-west-3', 'ap-northeast-1', 'ap-northeast-2', 'ap-east-1',
               'ap-southeast-1', 'ap-southeast-2', 'ap-south-1', 'eu-north-1',
               'eu-south-1', 'ap-northeast-3', 'ap-southeast-3', 'af-south-1']

REQUIRED = 'required'
VALIDATOR = 'validator'

PROJECT_PATH_CFG = 'project_path'
ACCOUNT_ID_CFG = 'account_id'
REGION_CFG = 'region'
LAMBDAS_ALIASES_NAME_CFG = 'lambdas_alias_name'
LOGS_EXPIRATION = 'logs_expiration'

AWS_ACCESS_KEY_ID_CFG = 'aws_access_key_id'
AWS_SECRET_ACCESS_KEY_CFG = 'aws_secret_access_key'
AWS_SESSION_TOKEN_CFG = 'aws_session_token'
DEPLOY_TARGET_BUCKET_CFG = 'deploy_target_bucket'
PROJECTS_MAPPING_CFG = 'build_projects_mapping'
RESOURCES_SUFFIX_CFG = 'resources_suffix'
RESOURCES_PREFIX_CFG = 'resources_prefix'
IAM_SUFFIX_CFG = 'iam_suffix'
EXTENDED_PREFIX_MODE_CFG = 'extended_prefix_mode'
EXTENDED_PREFIX_PATTERN = '^[a-z0-9-]+$'

USE_TEMP_CREDS_CFG = 'use_temp_creds'
SERIAL_NUMBER_CFG = 'serial_number'
TEMP_AWS_ACCESS_KEY_ID_CFG = 'temp_aws_access_key_id'
TEMP_AWS_SECRET_ACCESS_KEY_CFG = 'temp_aws_secret_access_key'
TEMP_AWS_SESSION_TOKEN_CFG = 'temp_aws_session_token'
EXPIRATION_CFG = 'expiration'
SESSION_DURATION_CFG = 'session_duration'
ACCESS_ROLE_CFG = 'access_role'
IAM_PERMISSIONS_BOUNDARY_CFG = 'iam_permissions_boundary'
LOCK_LIFETIME_MINUTES_CFG = 'lock_lifetime_minutes'

TAGS_CFG = 'tags'

PYTHON_LANGUAGE_NAME = 'python'
NODEJS_LANGUAGE_NAME = 'nodejs'
JAVA_LANGUAGE_NAME = 'java'
SWAGGER_UI_NAME = 'swagger_ui'

ALLOWED_RUNTIME_LANGUAGES = [PYTHON_LANGUAGE_NAME,
                             JAVA_LANGUAGE_NAME,
                             NODEJS_LANGUAGE_NAME,
                             SWAGGER_UI_NAME]

REQUIRED_PARAM_ERROR = 'The required key {} is missing'
UNKNOWN_PARAM_MESSAGE = 'Unknown parameter(s) in the configuration file: {}'

USER_LOG = get_user_logger()


class ConfigValidator:

    def __init__(self, config_dict) -> None:
        self._config_dict = config_dict
        self._extended_prefix_mode = config_dict.get(EXTENDED_PREFIX_MODE_CFG)
        self._fields_validators_mapping = {
            PROJECT_PATH_CFG: {
                REQUIRED: True,
                VALIDATOR: self._validate_project_path},
            ACCOUNT_ID_CFG: {
                REQUIRED: True,
                VALIDATOR: self._validate_account_id},
            REGION_CFG: {
                REQUIRED: True,
                VALIDATOR: self._validate_region},
            DEPLOY_TARGET_BUCKET_CFG: {
                REQUIRED: True,
                VALIDATOR: self._validate_bundle_bucket_name},
            PROJECTS_MAPPING_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_project_mapping},
            AWS_ACCESS_KEY_ID_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_access_key},
            AWS_SECRET_ACCESS_KEY_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_secret_access_key},
            AWS_SESSION_TOKEN_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_session_token},
            RESOURCES_PREFIX_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_resource_prefix},
            RESOURCES_SUFFIX_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_resources_prefix_suffix},
            IAM_SUFFIX_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_resources_prefix_suffix
            },
            EXTENDED_PREFIX_MODE_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_extended_prefix_mode
            },
            USE_TEMP_CREDS_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_use_temp_creds
            },
            SERIAL_NUMBER_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_serial_number
            },
            SESSION_DURATION_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_session_duration,
            },
            TEMP_AWS_SECRET_ACCESS_KEY_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_access_key
            },
            TEMP_AWS_ACCESS_KEY_ID_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_secret_access_key
            },
            TEMP_AWS_SESSION_TOKEN_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_session_token
            },
            EXPIRATION_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_expiration
            },
            ACCESS_ROLE_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_access_role
            },
            TAGS_CFG: {
                REQUIRED: False,
                VALIDATOR: self.validate_tags
            },
            IAM_PERMISSIONS_BOUNDARY_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_iam_permissions_boundary
            },
            LOCK_LIFETIME_MINUTES_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_lock_lifetime_minutes
            }
        }

    def validate(self):
        error_messages = {}
        unknown_params = set(self._config_dict.keys()) - set(
            self._fields_validators_mapping.keys())
        if unknown_params:
            USER_LOG.warn(UNKNOWN_PARAM_MESSAGE.format(unknown_params))

        for key, validation_rules in self._fields_validators_mapping.items():
            value = self._config_dict.get(key)
            is_required = validation_rules.get(REQUIRED)
            if is_required and not value:
                error_messages[key] = REQUIRED_PARAM_ERROR.format(key)
                continue
            if value:
                validator_func = validation_rules.get(VALIDATOR)
                validation_errors = validator_func(key, value)
                if validation_errors:
                    error_messages[key] = validation_errors
        return error_messages

    def _validate_project_path(self, key, value):
        str_error = self._assert_value_is_str(key, value)
        if str_error:
            return [str_error]
        errors = []
        if len(value) == 0:
            errors.append(f'{key} must not be empty')
        if not os.path.exists(value):
            errors.append(f'The path {value} specified in {key} must exist')
        return errors

    @staticmethod
    def _validate_account_id(key, value):
        errors = []
        try:
            int(value)
        except TypeError:
            errors.append(f'{key} must be int, not {type(value)}')
            return errors
        if len(str(value)) != 12:
            errors.append(f'{key} must be a 12-digit number')
        return errors

    def _validate_region(self, key, value):
        str_error = self._assert_value_is_str(key, value)
        if str_error:
            return [str_error]
        if value not in ALL_REGIONS:
            return [
                f'{key} value must be one of {ALL_REGIONS}, but is {value}'
            ]

    def _validate_bundle_bucket_name(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]

        errors = []
        # check min length
        name = re.compile(
            NAMED_S3_URI_PATTERN).match(value).groupdict().get('name')
        if len(name) < MIN_BUCKET_NAME_LEN or len(name) > MAX_BUCKET_NAME_LEN:
            errors.append(f'The length of {key} must be between '
                          f'{MIN_BUCKET_NAME_LEN} and {MAX_BUCKET_NAME_LEN} '
                          f'characters long but not {len(name)}')
        return errors

    def _validate_project_mapping(self, key, value):
        errors = []
        if type(value) is not dict:
            errors.append(f'{key} must be type of dict')
            return errors
        project_path = self._config_dict.get(PROJECT_PATH_CFG)
        for key in value.keys():
            if key not in ALLOWED_RUNTIME_LANGUAGES:
                errors.append(f'{key} is not supported to be built')
                continue
            for build_key, paths in value.items():
                if not paths:
                    errors.append(f'The path in {build_key} project '
                                  f'mapping not specified')

                else:
                    for path in paths:
                        if not os.path.exists(os.path.join(
                                project_path, path)):
                            errors.append(
                                f'The path in {key}:{build_key} project '
                                f'mapping does not exists: {path}')
        return errors

    def _validate_aws_access_key(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]
        if len(value) < 16 or len(value) > 128:
            return [
                f'The length of {key} must be in a '
                f'range between 16 and 128 characters']

    def _validate_aws_secret_access_key(self, key, value):
        # the only constraint found
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]

    def _validate_aws_session_token(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]

    def _validate_use_temp_creds(self, key, value):
        bool_error = self._assert_value_is_bool(
            key=key, value=value
        )
        if bool_error:
            return [bool_error]

    def _validate_serial_number(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]

    def _validate_access_role(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]

    @staticmethod
    def validate_tags(key, value):
        errors = []
        if not value:
            return errors
        if not isinstance(value, dict):
            errors.append(f'\'{key}\' param must be a dictionary but '
                          f'not a \'{type(value).__name__}\'')
            return errors
        if len(value) > 50:
            errors.append(f'Each resource can have up to 50 user created tags.'
                          f' You have specified: {len(value)}')
        for tag_name, tag_value in value.items():
            if tag_name.startswith('aws:'):
                errors.append(f'\'{tag_name}\': you can\'t create, edit or '
                              f'delete a tag that begins with the \'aws:\' '
                              f'prefix.')
                if not 1 <= len(tag_name) <= 128:
                    errors.append(f'\'{tag_name}\': the tag key must be a '
                                  f'minimum of 1 and a maximum of 128 Unicode '
                                  f'characters')
                if not 0 <= len(tag_value) <= 256:
                    errors.append(f'\'{tag_value}\': the tag value must be a '
                                  f'minimum of 0 and a maximum of 256 Unicode '
                                  f'characters')
        return errors

    @staticmethod
    def _validate_iam_permissions_boundary(key, value):
        errors = []
        if not isinstance(value, str):
            return [f'\'{key}\' must have a string type']
        return errors

    @staticmethod
    def _validate_expiration(key, value):
        if not isinstance(value, datetime.datetime):
            return [f'\'{key}\' must be a valid ISO 8601 format string']
        return []

    @staticmethod
    def _validate_resources_prefix_suffix(key, value):
        str_error = ConfigValidator._assert_value_is_str(key=key, value=value)
        if str_error:
            return [str_error]
        if len(value) > 5:
            return [
                f'The length of {key} must be less or equal to 5 character']

    def _validate_resource_prefix(self, key, value):
        if self._extended_prefix_mode:
            return self._validate_resources_prefix_extended_mode(key, value)
        return self._validate_resources_prefix_suffix(key, value)

    @staticmethod
    def _validate_extended_prefix_mode(key, value):
        bool_error = ConfigValidator._assert_value_is_bool(
            key=key, value=value
        )
        if bool_error:
            return [bool_error]

    @staticmethod
    def _validate_resources_prefix_extended_mode(key, value):
        result = []
        str_error = ConfigValidator._assert_value_is_str(key=key, value=value)
        if str_error:
            result.append(str_error)
        if len(value) > 14:
            result.append(f'The length of {key} must be less or equal to 14 '
                          f'character')
        if '--' in value:
            result.append(f'The {key} must not contain two consecutive '
                          f'hyphens')
        if not value[0].isalpha():
            result.append(f'The first character of the {key} must be a letter')
        if not re.match(EXTENDED_PREFIX_PATTERN, value):
            result.append(f'The {key} must contain only lowercase letters, '
                          f'numbers, and hyphens')
        return result

    @staticmethod
    def validate_prefix_suffix(key, value):
        result = ConfigValidator._validate_resources_prefix_suffix(key, value)
        if result:
            return result[0]

    @staticmethod
    def validate_extended_prefix(key, value):
        result = ConfigValidator._validate_resources_prefix_extended_mode(
            key, value)
        if result:
            return result

    @staticmethod
    def _validate_session_duration(key, value):
        if not isinstance(value, int):
            return [f'\'{key}\' must a an integer']
        if value < 900:
            return [f'\'{key}\' must begin from 900 seconds']

    @staticmethod
    def _validate_lock_lifetime_minutes(key, value):
        if not isinstance(value, int):
            return [f'\'{key}\' must a an integer']
        if not 0 <= value <= 300:
            return [f'\'{key}\' value must be between 0 and 300 minutes']

    @staticmethod
    def _assert_value_is_str(key, value):
        if type(value) is not str:
            return f'{key} must be type of string'

    @staticmethod
    def _assert_value_is_bool(key, value):
        if type(value) is not bool:
            return f'{key} must be type of bool'
