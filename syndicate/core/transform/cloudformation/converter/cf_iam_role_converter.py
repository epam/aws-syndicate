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

from syndicate.connection.iam_connection import build_trusted_relationships
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_helper import to_logic_name


class CfIamRoleConverter(CfResourceConverter):

    def convert(self, name, meta):
        allowed_accounts = meta.get('allowed_accounts', [])
        principal_service = meta.get('principal_service')
        external_id = meta.get('external_id')
        trust_rltn = meta.get('trusted_relationships')
        trusted_relationships = build_trusted_relationships(
            allowed_account=list(allowed_accounts),
            allowed_service=principal_service,
            external_id=external_id,
            trusted_relationships=trust_rltn)

        custom_policies = meta.get('custom_policies', [])
        predefined_policies = meta.get('predefined_policies', [])
        policy_arns = []
        for policy in predefined_policies:
            policy_arns.append(Ref(policy))
        for policy in custom_policies:
            policy_arns.append(Ref(to_logic_name(policy)))

        role = iam.Role(to_logic_name(name))
        role.AssumeRolePolicyDocument = trusted_relationships
        role.RoleName = name
        role.ManagedPolicyArns = policy_arns
        self.template.add_resource(role)

        instance_profile = meta.get('instance_profile')
        if instance_profile and instance_profile.lower() == 'true':
            self.template.add_resource(
                self._instance_profile(profile_name=name))

    @staticmethod
    def _instance_profile(profile_name):
        logic_id = to_logic_name(profile_name)
        instance_profile = iam.InstanceProfile(logic_id)
        instance_profile.InstanceProfileName = profile_name
        instance_profile.Roles = [Ref(logic_id)]
        return instance_profile
