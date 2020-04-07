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
import os

MIN_BUCKET_NAME_LEN = 3
MAX_BUCKET_NAME_LEN = 63

ALL_REGIONS = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'sa-east-1',
               'ca-central-1', 'eu-west-1', 'eu-central-1', 'eu-west-2',
               'eu-west-3', 'ap-northeast-1', 'ap-northeast-2',
               'ap-southeast-1', 'ap-southeast-2', 'ap-south-1', 'eu-north-1']

REQUIRED = 'required'
VALIDATOR = 'validator'

PROJECT_PATH_CFG = 'project_path'
ACCOUNT_ID_CFG = 'account_id'
REGION_CFG = 'region'
LAMBDAS_ALIASES_NAME_CFG = 'lambdas_alias_name'

AWS_ACCESS_KEY_ID_CFG = 'aws_access_key_id'
AWS_SECRET_ACCESS_KEY_CFG = 'aws_secret_access_key'
DEPLOY_TARGET_BUCKET_CFG = 'deploy_target_bucket'
PROJECTS_MAPPING_CFG = 'build_projects_mapping'
RESOURCES_SUFFIX_CFG = 'resources_suffix'
RESOURCES_PREFIX_CFG = 'resources_prefix'

PYTHON_BUILD_TOOL_NAME = 'python'
NODE_BUILD_TOOL_NAME = 'node'
MVN_BUILD_TOOL_NAME = 'mvn'
ALLOWED_BUILD_TOOLS = [PYTHON_BUILD_TOOL_NAME,
                       MVN_BUILD_TOOL_NAME,
                       NODE_BUILD_TOOL_NAME]

REQUIRED_PARAM_ERROR = 'The required key {} is missing'


class ConfigValidator:

    def __init__(self, config_dict) -> None:
        self._config_dict = config_dict
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
                REQUIRED: True,
                VALIDATOR: self._validate_project_mapping},
            AWS_ACCESS_KEY_ID_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_access_key},
            AWS_SECRET_ACCESS_KEY_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_aws_secret_access_key},
            RESOURCES_PREFIX_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_resources_prefix_suffix},
            RESOURCES_SUFFIX_CFG: {
                REQUIRED: False,
                VALIDATOR: self._validate_resources_prefix_suffix}
        }

    def validate(self):
        error_messages = {}
        for key, value in self._config_dict.items():
            validation_rules = self._fields_validators_mapping.get(key)
            if not validation_rules:
                raise AssertionError(
                    f'There is no validator for the configuration field {key}')

            is_required = validation_rules.get(REQUIRED)
            if is_required:
                if not value:
                    error_messages[key] = REQUIRED_PARAM_ERROR.format(key)
                    continue

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
        except TypeError as e:
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
        if len(value) < MIN_BUCKET_NAME_LEN or len(
                value) > MAX_BUCKET_NAME_LEN:
            errors.append(f'The length of {key} must be between '
                          f'{MIN_BUCKET_NAME_LEN} and {MAX_BUCKET_NAME_LEN} '
                          f'characters long')
        return errors

    def _validate_project_mapping(self, key, value):
        errors = []
        if type(value) is not dict:
            errors.append(f'{key} must be type of dict')
            return errors
        project_path = self._config_dict.get(PROJECT_PATH_CFG)
        for key in value.keys():
            if key not in ALLOWED_BUILD_TOOLS:
                errors.append(f'{key} is not supported to be built')
                continue
            for build_key, paths in value.items():
                for path in paths:
                    if not os.path.exists(os.path.join(project_path, path)):
                        errors.append(f'The path in {key}:{build_key} project '
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

    def _validate_resources_prefix_suffix(self, key, value):
        str_error = self._assert_value_is_str(key=key,
                                              value=value)
        if str_error:
            return [str_error]
        if len(value) > 5:
            return [
                f'The length of {key} must be less or equal to 5 character']

    @staticmethod
    def _assert_value_is_str(key, value):
        if type(value) is not str:
            return f'{key} must be type of string'
