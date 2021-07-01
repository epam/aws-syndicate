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
from troposphere import Template

from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer
from syndicate.core.transform.cloudformation.converter.cf_iam_managed_policy_converter import \
    CfIamManagedPolicyConverter
from syndicate.core.transform.cloudformation.converter.cf_iam_role_converter import CfIamRoleConverter
from syndicate.core.transform.cloudformation.converter.cf_lambda_function_converter import CfLambdaFunctionConverter


class CloudFormationTransformer(BuildMetaTransformer):

    def __init__(self):
        super().__init__()
        self.template = Template()

    def output_file_name(self) -> str:
        return 'cloudformation_template.json'

    def _transform_iam_managed_policy(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfIamManagedPolicyConverter)

    def _transform_iam_role(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfIamRoleConverter)

    def _transform_lambda(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfLambdaFunctionConverter)

    def convert_resources(self, name, resource, converter_type):
        converter = converter_type(
            config=self.config,
            resources_provider=self.resources_provider)
        for res in converter.convert(name=name, resource=resource):
            self.template.add_resource(res)

    def _compose_template(self):
        return self.template.to_json()
