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

from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import iam_managed_policy_logic_name


class CfIamManagedPolicyConverter(CfResourceConverter):

    def convert(self, name, meta):
        logic_name = iam_managed_policy_logic_name(name)
        policy = iam.ManagedPolicy(logic_name)
        policy.ManagedPolicyName = name
        policy.PolicyDocument = meta['policy_content']
        self.template.add_resource(policy)
