#  Copyright 2021 EPAM Systems, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import re

from syndicate.connection import IAMConnection
from syndicate.core.helper import prettify_json
from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer


class CloudFormationTransformer(BuildMetaTransformer):

    def __init__(self):
        super().__init__()
        self.resources = dict()

    def output_file_name(self) -> str:
        return 'cloudformation_template.json'

    def _add_resource(self, name, transformed_resource):
        logic_id = self._to_logic_id(name)
        self.resources[logic_id] = transformed_resource

    def _transform_iam_managed_policy(self, name, resource):
        self._add_resource(name, {
            'Type': 'AWS::IAM::ManagedPolicy',
            'Properties': {
                'ManagedPolicyName': name,
                'PolicyDocument': resource['policy_content']
            }
        })

    def _transform_iam_role(self, name, resource):
        allowed_accounts = resource.get('allowed_accounts', [])
        principal_service = resource.get('principal_service')
        external_id = resource.get('external_id')
        trust_rltn = resource.get('trusted_relationships')
        trusted_relationships = IAMConnection.build_trusted_relationships(
            allowed_account=list(allowed_accounts),
            allowed_service=principal_service,
            external_id=external_id,
            trusted_relationships=trust_rltn)

        custom_policies = resource.get('custom_policies', [])
        predefined_policies = resource.get('predefined_policies', [])
        policy_arns = []
        for policy in predefined_policies:
            policy_arns.append(self._ref(policy))
        for policy in custom_policies:
            policy_arns.append(self._ref(self._to_logic_id(policy)))

        self._add_resource(name, {
            'Type': 'AWS::IAM::Role',
            'Properties': {
                'ManagedPolicyArns': policy_arns,
                'AssumeRolePolicyDocument': trusted_relationships,
                'RoleName': name
            }
        })
        instance_profile = resource.get('instance_profile')
        if instance_profile.lower() == 'true':
            self._add_instance_profile(name)

    def _transform_lambda(self, name, resource):
        self._add_resource(name, {
            # 'Type': 'AWS::Lambda::Function',
            # 'Properties': {
            #     'Code': Code,
            #     'CodeSigningConfigArn': String,
            #     'DeadLetterConfig': DeadLetterConfig,
            #     'Description': String,
            #     'Environment': Environment,
            #     'FileSystemConfigs': [FileSystemConfig, ...],
            #     'FunctionName': String,
            #     'Handler': String,
            #     'ImageConfig': ImageConfig,
            #     'KmsKeyArn': String,
            #     'Layers': [String, ...],
            #     'MemorySize': Integer,
            #     'PackageType': String,
            #     'ReservedConcurrentExecutions': Integer,
            #     'Role': String,
            #     'Runtime': resource['runtime'],
            #     'Timeout': resource['timeout']
            # }
        })

    def _add_instance_profile(self, name):
        self._add_resource('{}_instance-profile'.format(name), {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {
                "InstanceProfileName": name,
                "Roles": [self._ref(self._to_logic_id(name))]
            }
        })

    def _compose_template(self):
        return prettify_json({
            'Resources': self.resources
        })

    @staticmethod
    def _to_logic_id(logic_id):
        name_components = re.split('[^A-Za-z0-9]', logic_id)
        return ''.join(x.title() for x in name_components)

    @staticmethod
    def _ref(name):
        return {'Ref': name}
