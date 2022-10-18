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
from troposphere import Ref, iam

from syndicate.connection.iam_connection import IAMConnection
from syndicate.commons.log_helper import get_user_logger
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import (to_logic_name, iam_role_logic_name, is_arn,
                                  iam_managed_policy_logic_name,
                                  iam_instance_profile_logic_name)

_LOG = get_user_logger()


class CfIamRoleConverter(CfResourceConverter):

    def convert(self, name, meta):
        role = iam.Role(iam_role_logic_name(name))
        role.RoleName = name
        role.Policies = []
        role.ManagedPolicyArns = self._prepare_policy_arns(meta)
        role.AssumeRolePolicyDocument = \
            self._build_assume_role_policy_document(meta)
        self.template.add_resource(role)

        instance_profile = meta.get('instance_profile')
        if instance_profile and str(instance_profile).lower() == 'true':
            self._convert_instance_profile(role_name=name)

    def _prepare_policy_arns(self, meta):
        custom_policies = meta.get('custom_policies') or []
        predefined_policies = meta.get('predefined_policies') or []
        policy_arns = []
        for policy in predefined_policies:
            iam_service = self.resources_provider.iam()
            policy_arn = iam_service.iam_conn.get_policy_arn(
                policy, policy_scope='AWS')
            if not policy_arn:
                _LOG.warning(f'AWS-managed policy with name \'{policy}\' '
                             f'not found. Skipping...')
                continue
            policy_arns.append(policy_arn)
        for policy in custom_policies:
            policy_arns.append(Ref(iam_managed_policy_logic_name(policy)))
        return policy_arns

    @staticmethod
    def _build_assume_role_policy_document(meta):
        allowed_accounts = meta.get('allowed_accounts', [])
        principal_service = meta.get('principal_service')
        external_id = meta.get('external_id')
        trusted_relationships = meta.get('trusted_relationships')
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
        return trusted_relationships

    def _convert_instance_profile(self, role_name):
        logic_name = iam_instance_profile_logic_name(role_name)
        instance_profile = iam.InstanceProfile(logic_name)
        instance_profile.InstanceProfileName = role_name
        instance_profile.Roles = [Ref(iam_role_logic_name(role_name))]
        self.template.add_resource(instance_profile)

    @staticmethod
    def convert_inline_policy(role, policy_name, policy_document):
        logic_name = to_logic_name('IAMPolicy', policy_name)
        policy = iam.PolicyType(logic_name)
        policy.PolicyDocument = policy_document
        policy.PolicyName = policy_name
        policy.Roles = [role if isinstance(role, str) else role.ref(), ]
        return policy

    @staticmethod
    def attach_managed_policy(role, policy):
        if is_arn(policy):
            if policy not in role.ManagedPolicyArns:
                role.ManagedPolicyArns.append(policy)
        else:
            ref = Ref(policy)
            if ref not in role.ManagedPolicyArns:
                role.ManagedPolicyArns.append(ref)
