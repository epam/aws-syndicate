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
from boto3 import client

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.connection.iam_connection import IAMConnection

_LOG = get_logger('syndicate.connection.cognito_identity_connection')


@apply_methods_decorator(retry)
class CognitoIdentityConnection(object):
    """ Cognito identity connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region,
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('cognito-identity', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Cognito identity connection.')

    def create_identity_pool(self, pool_name, provider_name=None,
                             allow_unauthenticated=False, login_providers=None,
                             open_id_connect_provider_arns=None,
                             cognito_identity_providers=None,
                             saml_provider_arns=None):
        """ Crete Cognito identity pool and get identity pool id.

        :type pool_name: str
        :type provider_name: str ('login.provider.com')
        :type allow_unauthenticated: bool
        :type login_providers: dict
        :type open_id_connect_provider_arns: list
        :type cognito_identity_providers: list
        :type saml_provider_arns: list
        """
        params = dict(IdentityPoolName=pool_name,
                      AllowUnauthenticatedIdentities=allow_unauthenticated)
        if provider_name:
            params['DeveloperProviderName'] = provider_name
        if login_providers:
            params['SupportedLoginProviders'] = login_providers
        if open_id_connect_provider_arns:
            params['OpenIdConnectProviderARNs'] = open_id_connect_provider_arns
        if cognito_identity_providers:
            params['CognitoIdentityProviders'] = cognito_identity_providers
        if saml_provider_arns:
            params['SamlProviderARNs'] = saml_provider_arns

        response = self.client.create_identity_pool(**params)
        return response.get('IdentityPoolId')

    def set_role(self, identity_pool_id, authenticated_role_name,
                 unauthenticated_role_name=None):
        """ Set role for cognito identity pool authenticated and
        unauthenticated users.

        :type identity_pool_id: str
        :type authenticated_role_name: str
        :type unauthenticated_role_name: str
        """
        if not (authenticated_role_name or unauthenticated_role_name):
            return
        iam_conn = IAMConnection(None, self.aws_access_key_id,
                                 self.aws_secret_access_key,
                                 self.aws_session_token)
        params = dict(IdentityPoolId=identity_pool_id, Roles={})
        if authenticated_role_name:
            auth_role_arn = iam_conn.check_if_role_exists(
                authenticated_role_name)
            if auth_role_arn:
                params['Roles']['authenticated'] = auth_role_arn
        if unauthenticated_role_name:
            unauth_role_arn = iam_conn.check_if_role_exists(
                unauthenticated_role_name)
            if unauth_role_arn:
                params['Roles']['unauthenticated'] = unauth_role_arn
        self.client.set_identity_pool_roles(**params)

    def list_existing_pools(self):
        """ Get list of existing identity pools."""
        existing_pools = []
        identity_pools = self.client.list_identity_pools(MaxResults=60)
        existing_pools.extend(identity_pools.get('IdentityPools'))
        token = identity_pools.get('NextToken')
        while token:
            identity_pools = self.client.list_identity_pools(MaxResults=60,
                                                             NextToken=token)
            existing_pools.extend(identity_pools.get('IdentityPools'))
            token = identity_pools['NextToken']
        return existing_pools

    def if_pool_exists_by_name(self, pool_name):
        """ Check if pool exists by name.

        :type pool_name: str
        """
        pools = self.list_existing_pools()
        if pools:
            for each in pools:
                if each['IdentityPoolName'] == pool_name:
                    return each['IdentityPoolId']

    def describe_identity_pool(self, identity_pool_id):
        return self.client.describe_identity_pool(
            IdentityPoolId=identity_pool_id)

    def remove_identity_pool(self, identity_pool_id):
        """ Remove identity pool by id.

        :type identity_pool_id: str
        """
        self.client.delete_identity_pool(IdentityPoolId=identity_pool_id)

    def list_all_identities_ids_in_pool(self, identity_pool_name):
        """ Lists all identities ids in identity pool"""
        pool_id = self.if_pool_exists_by_name(identity_pool_name)
        if pool_id:
            response = self.client.list_identities(IdentityPoolId=pool_id,
                                                   MaxResults=60)
            identities_list = response['Identities']
            token = response.get('NextToken')
            while token:
                response = self.client.list_identities(IdentityPoolId=pool_id,
                                                       MaxResults=60)
                identities_list.append(response['Identities'])
                token = response['NextToken']

            identity_ids_list = []
            for identity in identities_list:
                identity_ids_list.append(identity.get('IdentityId'))
            return identity_ids_list

    def remove_specified_identities_in_pool(self, identities_to_delete):
        """ Removes specified identities from specified pool"""
        response = self.client.delete_identities(
            IdentityIdsToDelete=identities_to_delete)
        return response
