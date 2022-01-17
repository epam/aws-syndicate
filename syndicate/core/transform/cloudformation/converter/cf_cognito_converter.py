"""
    Copyright 2021 EPAM Systems, Inc.

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
from troposphere import cognito

from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, iam_role_logic_name


class CfCognitoConverter(CfResourceConverter):

    def convert(self, name, meta):
        open_id_provider_names = meta.get('open_id_providers', [])
        account_id = self.config.account_id
        open_id_arns = ['arn:aws:iam::{0}:oidc-provider/{1}'.format(
            account_id, n) for n in open_id_provider_names]

        logic_name = to_logic_name('CognitoIdentityPool', name)
        identity_pool = cognito.IdentityPool(logic_name)
        identity_pool.AllowUnauthenticatedIdentities = False
        self.template.add_resource(identity_pool)

        provider_name = meta.get('provider_name')
        if provider_name:
            identity_pool.DeveloperProviderName = provider_name

        if open_id_arns:
            identity_pool.OpenIdConnectProviderARNs = open_id_arns

        auth_role_name = meta.get('auth_role')
        unauth_role_name = meta.get('unauth_role')
        if auth_role_name or unauth_role_name:
            role_attachment = cognito.IdentityPoolRoleAttachment(
                to_logic_name('CognitoIdentityPoolRoleAttachment', name))
            role_attachment.IdentityPoolId = identity_pool.ref()
            self.template.add_resource(role_attachment)

            roles = {}
            if auth_role_name:
                auth_role = self.get_resource(
                    iam_role_logic_name(auth_role_name))
                if auth_role:
                    roles['authenticated'] = auth_role.get_att('Arn')
            if unauth_role_name:
                unauth_role = self.get_resource(
                    iam_role_logic_name(unauth_role_name))
                if unauth_role:
                    roles['unauthenticated'] = unauth_role.get_att('Arn')
            role_attachment.Roles = roles
