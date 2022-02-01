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
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection import ResourceGroupsTaggingAPIConnection
from syndicate.core.constants import LAMBDA_TYPE

_LOG = get_logger('syndicate.core.resources.group_tagging_api_resource')
USER_LOG = get_user_logger()


class TagsApiResource:
    def __init__(self, connection: ResourceGroupsTaggingAPIConnection):
        self.connection = connection
        self.resource_type_to_preprocessor_mapping = {
            LAMBDA_TYPE: self._preprocess_lambda_arn
        }
        from syndicate.core import CONFIG
        self.tags = CONFIG.tags

    @staticmethod
    def _preprocess_lambda_arn(arn: str, meta: dict):
        """Extracts lambda's arn without version and alias """
        lambda_name = meta['resource_name']
        processed_arn = arn[:arn.index(lambda_name) + len(lambda_name)]
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

    def apply_tags(self, output: dict):
        if not self.tags:
            USER_LOG.info('No tags are specified in config. Skipping...')
            return
        arns = self._extract_arns(output)
        failed_resources = self.connection.tag_resources(resources_arns=arns,
                                                         tags=self.tags)
        if not failed_resources:
            USER_LOG.info('Tags were successfully applied to all resources')
        else:
            USER_LOG.warn(f'Couldn\'t apply tags for resources: '
                          f'{failed_resources.keys()}')

    def remove_tags(self, output: dict):
        if not self.tags:
            USER_LOG.info('No tags are specified in config. Skipping...')
            return
        arns = self._extract_arns(output)
        failed_resources = self.connection.untag_resources(
            resources_arns=arns, tag_keys=list(self.tags.keys()))
        if not failed_resources:
            USER_LOG.info('Tags were successfully removed from all resources')
        else:
            USER_LOG.warn(f'Couldn\'t remove tags from resources: '
                          f'{failed_resources.keys()}')
