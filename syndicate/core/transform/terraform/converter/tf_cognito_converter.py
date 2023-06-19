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
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_cognito_identity_pool_id, build_role_arn_ref


class CognitoConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        provider_name = resource.get('provider_name')
        open_id_provider_names = resource.get('open_id_providers', [])
        open_id_arns = ['arn:aws:iam::{0}:oidc-provider/{1}'.format(
            self.config.account_id, n) for n in open_id_provider_names]
        identity_pool = cognito_identity_pool(identity_pool_name=name,
                                              provider_name=provider_name,
                                              open_id_connect_provider_arns=open_id_arns)
        self.template.add_aws_cognito_identity_pool(meta=identity_pool)

        auth_role = resource.get('auth_role')
        unauth_role = resource.get('unauth_role')
        pool_attachment = aws_cognito_identity_pool_attachment(
            identity_pool_name=name,
            authenticated=auth_role,
            unauthenticated=unauth_role)
        self.template.add_aws_cognito_identity_pool_roles_attachment(
            pool_attachment)


def cognito_identity_pool(identity_pool_name,
                          allow_unauthenticated_identities=False,
                          provider_name=None,
                          login_providers=None,
                          open_id_connect_provider_arns=None,
                          cognito_identity_providers=None,
                          saml_provider_arns=None):
    identity_pool = {
        "identity_pool_name": identity_pool_name
    }

    if allow_unauthenticated_identities:
        identity_pool[
            'allow_unauthenticated_identities'] = allow_unauthenticated_identities
    if provider_name:
        identity_pool['developer_provider_name'] = provider_name
    if login_providers:
        identity_pool['supported_login_providers'] = login_providers
    if open_id_connect_provider_arns:
        identity_pool[
            'openid_connect_provider_arns'] = open_id_connect_provider_arns
    if cognito_identity_providers:
        identity_pool[
            'cognito_identity_providers'] = cognito_identity_providers
    if saml_provider_arns:
        identity_pool['saml_provider_arns'] = saml_provider_arns

    resource = {
        identity_pool_name: identity_pool
    }
    return resource


def aws_cognito_identity_pool_attachment(identity_pool_name, authenticated,
                                         unauthenticated):
    identity_pool_id_ref = build_cognito_identity_pool_id(
        pool_name=identity_pool_name)
    attachment = {
        "identity_pool_id": identity_pool_id_ref
    }

    roles = {}
    if authenticated:
        auth_role_ref = build_role_arn_ref(role_name=authenticated)
        roles['authenticated'] = auth_role_ref

    if unauthenticated:
        unauth_role_ref = build_role_arn_ref(role_name=unauthenticated)
        roles['unauthenticated']: unauth_role_ref

    if roles:
        attachment.update({'roles': roles})

    resource = {
        "attachment": attachment
    }
    return resource
