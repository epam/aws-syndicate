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
import json

from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_policy_arn_ref
from syndicate.connection.iam_connection import IAMConnection
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class IamRoleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        allowed_accounts = resource.get('allowed_accounts', [])
        principal_service = resource.get('principal_service')
        external_id = resource.get('external_id')
        trusted_relationships = resource.get('trusted_relationships')

        policy_arns = self._prepare_policy_arns(resource=resource)

        if not trusted_relationships:
            trusted_relationships = IAMConnection.empty_trusted_relationships()
        if allowed_accounts:
            trusted_accounts = IAMConnection.set_allowed_account(
                allowed_accounts, external_id, 'create')
            trusted_relationships['Statement'].append(trusted_accounts)
        if principal_service:
            trusted_services = IAMConnection.set_allowed_service(
                principal_service, 'create')
            trusted_relationships['Statement'].append(trusted_services)

        policy_json = json.dumps(trusted_relationships)
        resource_template = iam_role(role_name=name,
                                     policy_arns=policy_arns,
                                     assume_role_policy=policy_json)
        self.template.add_aws_iam_role(meta=resource_template)

    def _prepare_policy_arns(self, resource):
        custom_policies = resource.get('custom_policies', [])
        predefined_policies = resource.get('predefined_policies', [])
        policy_arns = []
        for policy in predefined_policies:
            iam_service = self.resources_provider.iam()
            policy_arn = iam_service.iam_conn.get_policy_arn(policy)
            if policy_arn:
                policy_arns.append(policy_arn)
        for policy in custom_policies:
            policy_arns.append(build_policy_arn_ref(policy_name=policy))
        return policy_arns


def iam_role(role_name,
             assume_role_policy,
             policy_arns=None):
    role_params = {
        'assume_role_policy': assume_role_policy,
        'name': role_name
    }

    if policy_arns:
        role_params['managed_policy_arns'] = policy_arns

    resource = {
        role_name: role_params
    }
    return resource
