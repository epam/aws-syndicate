"""
    Copyright 2018 EPAM Systems, Inc.

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
from syndicate.commons.log_helper import get_logger
from syndicate.core.resources.base_resource import BaseResource
from syndicate.connection import ResourceGroupsTaggingAPIConnection
from syndicate.core.constants import LAMBDA_TYPE


_LOG = get_logger('syndicate.core.resources.group_tagging_api_resource')


class GroupsTaggingApiResource(BaseResource):
    def __init__(self, connection: ResourceGroupsTaggingAPIConnection):
        self.connection = connection
        self.resource_type_to_preprocessor_mapping = {
            LAMBDA_TYPE: self._preprocess_lambda_arn
        }
        self.output = None

    @staticmethod
    def _preprocess_lambda_arn(arn: str, meta: dict):
        """Extracts lambda's arn without version and alias """
        lambda_name = meta['resource_name']
        processed_arn = arn[:arn.index(lambda_name)+len(lambda_name)]
        _LOG.debug(f'Processing lambda\'s arn from \'{arn}\' '
                   f'to \'{processed_arn}\'')
        return processed_arn

    def _extract_arns(self, output: dict) -> list:
        arns = []
        _LOG.info(f'Extracting and processing arns from output')
        for arn, meta in output.items():
            resource_type = meta['resource_meta']['resource_type']
            processor_func = self.resource_type_to_preprocessor_mapping.get(
                resource_type)
            if processor_func:
                arn = processor_func(arn, meta)
            arns.append(arn)
        return arns

    def tag_resources_from_output(self, output: dict, tags: dict):
        arns = self._extract_arns(output)
        failed_resources = self.connection.tag_resources(resources_arns=arns,
                                                         tags=tags)
        if failed_resources:
            _LOG.warn(f'Couldn\'t tag resources: {failed_resources.keys()}')
            return failed_resources
