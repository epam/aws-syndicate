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
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import (
    unpack_kwargs, dict_keys_to_capitalized_camel_case)
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, \
    assert_required_params, assert_possible_values

_LOG = get_logger('syndicate.core.resources.cognito_user_pool_resource')


class CognitoUserPoolResource(BaseResource):

    def __init__(self, cognito_idp_conn, account_id,
                 region) -> None:
        self.connection = cognito_idp_conn
        self.account_id = account_id
        self.region = region

    def create_cognito_user_pool(self, args):
        """ Create Cognito user pool in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_cognito_user_pool_from_meta,
                                args)

    def describe_user_pool(self, name, meta, pool_id=None):
        if not pool_id:
            pool_id = self.connection.if_pool_exists_by_name(name)
        if not pool_id:
            return
        response = self.connection.describe_user_pool(pool_id)
        arn = f'arn:aws:cognito-idp:{self.region}:{self.account_id}:' \
              f'userpool/{pool_id}'
        return {
            arn: build_description_obj(response, name, meta)
        }

    def is_user_pool_exists(self, pool_id):
        try:
            return True if self.connection.describe_user_pool(pool_id) else \
                False
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn(f'Cognito user pool {pool_id} is not found!')
            else:
                raise e

    @unpack_kwargs
    def _create_cognito_user_pool_from_meta(self, name, meta):
        """ Create Cognito user pool for authentication.

        :type name: str
        :type meta: dict
        """
        pool_id = self.connection.if_pool_exists_by_name(name)
        if pool_id:
            _LOG.warn(f'%s cognito user pool exists.', name)
            return self.describe_user_pool(name=name, meta=meta,
                                           pool_id=pool_id)

        _LOG.info('Creating user pool %s', name)
        auto_verified_attributes = meta.get('auto_verified_attributes', [])
        if not isinstance(auto_verified_attributes, list):
            _LOG.warn('Incorrect value for auto_verified_attributes: %s, '
                      'it must be a list',
                      auto_verified_attributes)
            auto_verified_attributes = []
        assert_possible_values(auto_verified_attributes,
                                ['email', 'phone_number'])

        sms_configuration = meta.get('sms_configuration', {})
        if not isinstance(sms_configuration, dict):
            _LOG.warn('Incorrect value for auto_verified_attributes: %s, '
                      'it must be a dict',
                      sms_configuration)
            sms_configuration = {}
        if 'phone_number' in auto_verified_attributes:
            _LOG.warn(f"'phone_number' is inside {auto_verified_attributes}. "
                      f"Hence 'sns_caller_arn' must be in {sms_configuration}")
            assert_required_params(['sns_caller_arn'], sms_configuration)
        sms_configuration = dict_keys_to_capitalized_camel_case(
            sms_configuration)

        username_attributes = meta.get('username_attributes', [])
        if not isinstance(username_attributes, list):
            _LOG.warn('Incorrect value for username_attributes: %s, '
                      'it must be a list',
                      username_attributes)
            username_attributes = []
        assert_possible_values(username_attributes, ['email', 'phone_number'])

        policies = meta.get('password_policy')
        if policies:
            policies = self.__validate_policies(policies)

        pool_id = self.connection.create_user_pool(
            pool_name=name, auto_verified_attributes=auto_verified_attributes,
            sms_configuration=sms_configuration,
            username_attributes=username_attributes, policies=policies)

        custom_attributes = meta.get('custom_attributes')
        if custom_attributes:
            self.add_custom_attributes(pool_id, custom_attributes)
        client = meta.get('client')
        if client:
            self.connection.create_user_pool_client(
                user_pool_id=pool_id, **client)
        _LOG.info('Created cognito user pool %s', pool_id)
        return self.describe_user_pool(name=name, meta=meta, pool_id=pool_id)

    def remove_cognito_user_pools(self, args):
        self.create_pool(self._remove_cognito_user_pools, args)

    @unpack_kwargs
    def _remove_cognito_user_pools(self, arn, config):
        pool_id = config['description']['UserPool']['Id']
        try:
            self.connection.remove_user_pool(pool_id)
            _LOG.info('Cognito user pool %s was removed', pool_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Cognito user pool %s is not found', id)
            else:
                raise e

    def get_user_pool_id(self, name):
        """
        Returns user pools ID by its name

        :param name: user pools name
        :return: user pools ID
        """
        return self.connection.if_pool_exists_by_name(user_pool_name=name)

    def cognito_resource_identifier(self, name, output=None):
        if output:
            # cognito currently is not located in different regions
            # process only first object
            pool_output = list(output.items())[0][1]
            # find id from the output
            return pool_output['description']['UserPool']['Id']
        return self.connection.if_pool_exists_by_name(name)

    def add_custom_attributes(self, user_pool_id, attributes):
        custom_attributes = []
        for attr in attributes:
            attr['attribute_data_type'] = attr.pop('type')
            custom_attributes.append(dict_keys_to_capitalized_camel_case(attr))
        self.connection.add_custom_attributes(user_pool_id, custom_attributes)

    @staticmethod
    def __validate_policies(policies):
        if not policies.get('minimum_length'):
            policies['minimum_length'] = 6
        if not policies.get('require_uppercase'):
            policies['require_uppercase'] = True
        if not policies.get('require_symbols'):
            policies['require_symbols'] = True
        if not policies.get('require_lowercase'):
            policies['require_lowercase'] = True
        if not policies.get('require_numbers'):
            policies['require_numbers'] = True

        return {'PasswordPolicy': dict_keys_to_capitalized_camel_case(
            policies)}


