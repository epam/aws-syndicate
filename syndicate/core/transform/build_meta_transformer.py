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
from abc import abstractmethod

from syndicate.core.build.meta_processor import resolve_meta
from syndicate.core.constants import IAM_POLICY, IAM_ROLE, LAMBDA_TYPE


class BuildMetaTransformer(object):

    def __init__(self):
        from syndicate.core import CONFIG, RESOURCES_PROVIDER
        self.config = CONFIG
        self.resources_provider = RESOURCES_PROVIDER

        self.transformer_mapping = {
            IAM_POLICY: self._transform_iam_managed_policy,
            IAM_ROLE: self._transform_iam_role,
            LAMBDA_TYPE: self._transform_lambda
        }

    def transform_build_meta(self, build_meta):
        build_meta = resolve_meta(build_meta)
        for name, resource in build_meta.items():
            resource_type = resource.get('resource_type')
            transformer = self.transformer_mapping.get(resource_type)
            if transformer is None:
                raise ValueError(
                    "Transformation is not supported for resources "
                    "of the '{}' type".format(resource_type))
            transformer(name=name, resource=resource)
        return self._compose_template()

    @abstractmethod
    def output_file_name(self) -> str:
        pass

    @abstractmethod
    def _transform_iam_managed_policy(self, name, resource):
        pass

    @abstractmethod
    def _transform_iam_role(self, name, resource):
        pass

    @abstractmethod
    def _transform_lambda(self, name, resource):
        pass

    @abstractmethod
    def _compose_template(self):
        pass
