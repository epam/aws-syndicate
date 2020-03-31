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

_LOG = get_logger('syndicate.core.resources.cognito_identity_resource')


class CognitoResource(BaseResource):

    def __init__(self, cognito_conn, account_id, region) -> None:
        self.connection = cognito_conn
        self.account_id = account_id
        self.region = region

    def cognito_resource_identifier(self, name, output=None):
        if output:
            # cognito currently is not located in different regions
            # process only first object
            pool_output = list(output.items())[0][1]
            # find id from the output
            return pool_output['description']['IdentityPoolId']
        return self.connection.if_pool_exists_by_name(name)

    def create_cognito_identity_pool(self, args):
        """ Create Cognito identity pool in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_cognito_identity_pool_from_meta,
                                args)

    def describe_cognito_pool(self, name, meta, pool_id=None):
        if not pool_id:
            pool_id = self.connection.if_pool_exists_by_name(name)
        if not pool_id:
            return
        response = self.connection.describe_identity_pool(pool_id)
        arn = 'arn:aws:cognito-identity:{0}:{1}:identitypool/{2}'.format(
            self.region, self.account_id, pool_id)
        return {
            arn: build_description_obj(response, name, meta)
        }

    @unpack_kwargs
    def _create_cognito_identity_pool_from_meta(self, name, meta):
        """ Create Cognito identity pool for authentication.

        :type name: str
        :type meta: dict
        """
        pool_id = self.connection.if_pool_exists_by_name(name)
        if pool_id:
            _LOG.warn('%s cognito identity pool exists.', name)
            return self.describe_cognito_pool(name=name, meta=meta,
                                              pool_id=pool_id)

        _LOG.info('Creating identity pool %s', name)
        open_id_provider_names = meta.get('open_id_providers', [])
        open_id_arns = ['arn:aws:iam::{0}:oidc-provider/{1}'.format(
            self.account_id, n) for n in open_id_provider_names]
        pool_id = self.connection.create_identity_pool(
            pool_name=name, provider_name=meta.get('provider_name'),
            open_id_connect_provider_arns=open_id_arns)
        auth_role = meta.get('auth_role')
        unauth_role = meta.get('unauth_role')
        if auth_role or unauth_role:
            self.connection.set_role(pool_id, auth_role, unauth_role)
        _LOG.info('Created cognito identity pool %s', pool_id)
        return self.describe_cognito_pool(name=name, meta=meta,
                                          pool_id=pool_id)

    def remove_cognito_identity_pools(self, args):
        self.create_pool(self._remove_cognito_identity_pool, args)

    @unpack_kwargs
    def _remove_cognito_identity_pool(self, arn, config):
        pool_id = config['description']['IdentityPoolId']
        try:
            self.connection.remove_identity_pool(pool_id)
            _LOG.info('Cognito identity pool %s was removed', pool_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Cognito identity pool %s is not found', id)
            else:
                raise e
