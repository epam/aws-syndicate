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
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

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
        auto_verified_attributes = meta.get('auto_verified_attributes', None)
        if not auto_verified_attributes in ('phone_number', 'email', None):
            _LOG.warn('Incorrect value for auto_verified_attributes: %s',
                      auto_verified_attributes)
            auto_verified_attributes = None
        username_attributes = meta.get('username_attributes', None)
        if not username_attributes in ('phone_number', 'email', None):
            _LOG.warn('Incorrect value for username_attributes: %s',
                      username_attributes)
            username_attributes = None

        pool_id = self.connection.create_user_pool(
            pool_name=name, auto_verified_attributes=auto_verified_attributes,
            username_attributes=username_attributes)

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
