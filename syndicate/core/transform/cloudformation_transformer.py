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
from syndicate.core.constants import IAM_POLICY, IAM_ROLE, LAMBDA_TYPE
from syndicate.core.transform.build_meta_transformer import BuildMetaTransformer


class CloudFormationTransformer(BuildMetaTransformer):

    def __init__(self):
        super().__init__({
            IAM_POLICY: self.__transform_iam_managed_policy,
            IAM_ROLE: self.__transform_iam_role,
            LAMBDA_TYPE: self.__transform_iam_role
        })

    def output_file_name(self) -> str:
        return 'cloudformation_template.json'

    def __transform_iam_managed_policy(self, name, resource):
        return 'IAM policy'

    def __transform_iam_role(self, name, resource):
        return 'IAM role'

    def __transform_lambda(self, name, resource):
        return 'Lambda'

    def __compose_template(self):
        return 'TEMPLATE'
