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

_LOG = get_logger(__name__)


@apply_methods_decorator(retry())
class CognitoIdentityProviderConnection(object):
    """ Cognito identity provider connection class."""

    def __init__(self, client_config, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('cognito-idp', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token,
                             config=client_config)
        _LOG.debug('Opened new Cognito identity connection.')

    def create_user_pool(self, pool_name, auto_verified_attributes=None,
                         sms_configuration=None, username_attributes=None,
                         policies=None, tags=None):
        """
        Crete Cognito user pool and get user pool id.
        """
        params = dict(PoolName=pool_name)
        if auto_verified_attributes:
            params['AutoVerifiedAttributes'] = auto_verified_attributes
        if sms_configuration:
            params['SmsConfiguration'] = sms_configuration
        if username_attributes:
            params['UsernameAttributes'] = username_attributes
        if policies:
            params['Policies'] = policies
        if tags:
            params['UserPoolTags'] = tags

        response = self.client.create_user_pool(**params)
        return response['UserPool'].get('Id')

    def create_user_pool_client(
            self, user_pool_id, client_name, generate_secret=True,
            refresh_token_validity=None,
            read_attributes=None,
            write_attributes=None, explicit_auth_flows=None,
            supported_identity_providers=None,
            callback_urls=None, logout_urls=None, default_redirect_uri=None,
            allowed_oauth_flows=None, allowed_oauth_scopes=None,
            allowed_oauth_flows_user_pool_client=None,
            analytics_configuration=None, prevent_user_existence_errors=None,
            enable_token_revocation=None):
        params = dict(UserPoolId=user_pool_id, ClientName=client_name,
                      GenerateSecret=generate_secret)
        if refresh_token_validity:
            params.update(RefreshTokenValidity=refresh_token_validity)
        if read_attributes:
            params.update(ReadAttributes=read_attributes)
        if write_attributes:
            params.update(WriteAttributes=write_attributes)
        if explicit_auth_flows:
            params.update(ExplicitAuthFlows=explicit_auth_flows)
        if supported_identity_providers:
            params.update(
                SupportedIdentityProviders=supported_identity_providers)
        if callback_urls:
            params.update(CallbackURLs=callback_urls)
        if logout_urls:
            params.update(LogoutURLs=logout_urls)
        if default_redirect_uri:
            params.update(DefaultRedirectURI=default_redirect_uri)
        if allowed_oauth_flows:
            params.update(AllowedOAuthFlows=allowed_oauth_flows)
        if allowed_oauth_scopes:
            params.update(AllowedOAuthScopes=allowed_oauth_scopes)
        if allowed_oauth_flows_user_pool_client:
            params.update(AllowedOAuthFlowsUserPoolClient=
                          allowed_oauth_flows_user_pool_client)
        if analytics_configuration:
            params.update(AnalyticsConfiguration=analytics_configuration)
        if prevent_user_existence_errors:
            params.update(
                PreventUserExistenceErrors=prevent_user_existence_errors)
        if enable_token_revocation:
            params.update(EnableTokenRevocation=enable_token_revocation)

        response = self.client.create_user_pool_client(**params)
        return response['UserPoolClient'].get('ClientId')

    def list_user_pool_clients(self, cup_id):

        response = self.client.list_user_pool_clients(
            UserPoolId=cup_id,
            MaxResults=5
        )

        client_ids = [cup_client['ClientId'] for
                      cup_client in response['UserPoolClients']]
        next_token = response.get('NextToken')

        while next_token:
            response = self.client.list_user_pool_clients(
                UserPoolId=cup_id,
                MaxResults=5,
                NextToken=next_token
            )
            client_ids.extend([cup_client['ClientId'] for
                               cup_client in response['UserPoolClients']])
            next_token = response.get('NextToken')

        return client_ids

    def if_cup_client_exist(self, cup_name):

        cup_id = self.if_pool_exists_by_name(cup_name)
        if not cup_id:
            return

        client_ids = self.list_user_pool_clients(cup_id)

        if len(client_ids) == 1:
            return client_ids[0]
        if len(client_ids) > 1:
            _LOG.warn(f'Client ID of Cognito User Pool "{cup_name}" can\'t be '
                      f'identified unambiguously because there is more than '
                      f'one client in the Cognito User Pool. Determined IDs: '
                      f'"{client_ids}"')
        else:
            _LOG.warn(f'Clients not found in the Cognito User Pool with the '
                      f'name "{cup_name}"')

    def if_pool_exists_by_name(self, user_pool_name):
        ids = []
        paginator = self.client.get_paginator('list_user_pools')
        response = paginator.paginate(
            PaginationConfig={
                'MaxItems': 60,
                'PageSize': 10
            }
        )
        for page in response:
            ids.extend(
                [user_pool['Id'] for user_pool in page['UserPools'] if
                 user_pool['Name'] == user_pool_name]
            )
        next_token = response.resume_token
        while next_token:
            response = paginator.paginate(
                PaginationConfig={
                    'MaxItems': 60,
                    'PageSize': 10,
                    'StartingToken': next_token
                }
            )
            for page in response:
                ids.extend(
                    [user_pool['Id'] for user_pool in page['UserPools'] if
                     user_pool['Name'] == user_pool_name]
                )
            next_token = response.resume_token

        if len(ids) == 1:
            return ids[0]
        if len(ids) > 1:
            _LOG.warn(f'Cognito User Pool can\'t be identified unambiguously '
                      f'because there is more than one resource with the name '
                      f'"{user_pool_name}" in the region {self.region}. '
                      f'Determined IDs: "{ids}"')
        else:
            _LOG.warn(f'Cognito User Pool with the name "{user_pool_name}" '
                      f'not found in the region {self.region}')

    def describe_user_pool(self, user_pool_id):
        return self.client.describe_user_pool(UserPoolId=user_pool_id)

    def remove_user_pool(self, user_pool_id, log_not_found_error=True):
        """
        Removes user pool by id.

        :type user_pool_id: str
        :type log_not_found_error: boolean, parameter is needed for proper log
        handling in the retry decorator
        """
        self.client.delete_user_pool(UserPoolId=user_pool_id)

    def add_custom_attributes(self, user_pool_id, attributes):
        self.client.add_custom_attributes(UserPoolId=user_pool_id,
                                          CustomAttributes=attributes)
