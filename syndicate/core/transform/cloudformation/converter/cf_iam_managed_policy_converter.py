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
from troposphere import iam

from syndicate.core.transform.cloudformation.cf_transform_helper import to_logic_name
from syndicate.core.transform.cloudformation.converter.cf_resource_converter import CfResourceConverter


class CfIamManagedPolicyConverter(CfResourceConverter):

    def convert(self, name, meta):
        policy = iam.ManagedPolicy(to_logic_name(name))
        policy.ManagedPolicyName = name
        policy.PolicyDocument = meta['policy_content']
        self.template.add_resource(policy)
