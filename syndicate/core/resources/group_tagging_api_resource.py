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
from concurrent.futures import ThreadPoolExecutor, as_completed

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection import ResourceGroupsTaggingAPIConnection
from syndicate.core.constants import LAMBDA_TYPE, SWAGGER_UI_TYPE, \
    TAGS_RESOURCE_TYPE_CONFIG
from syndicate.core.resources.helper import chunks

_LOG = get_logger('syndicate.core.resources.group_tagging_api_resource')
USER_LOG = get_user_logger()


class TagsApiResource:
    def __init__(self, connection: ResourceGroupsTaggingAPIConnection):
        self.connection = connection
        self.resource_type_to_preprocessor_mapping = {
            LAMBDA_TYPE: self._preprocess_lambda_arn
        }
        self.post_deploy_tagging_types = TAGS_RESOURCE_TYPE_CONFIG[
            'post_deploy_tagging']
        self.untaggable_resource_types = TAGS_RESOURCE_TYPE_CONFIG[
            'untaggable']
        from syndicate.core import CONFIG
        self.tags = CONFIG.tags

    @staticmethod
    def _preprocess_lambda_arn(arn: str, meta: dict):
        """Extracts lambda's arn without version and alias """
        lambda_name = meta['resource_name']
        processed_arn = arn[:arn.index(lambda_name) + len(lambda_name)]
        _LOG.debug(f'Processing lambda\'s arn from \'{arn}\' '
                   f'to \'{processed_arn}\'')
        lambda_arn_params = processed_arn.split(':')
        cw_lg_arn = (f'arn:aws:logs:{lambda_arn_params[3]}:'
                     f'{lambda_arn_params[4]}:log-group:/aws/lambda/'
                     f'{lambda_name}')
        _LOG.debug(f'For lambda \'{lambda_name}\' resolved CloudWatch logs '
                   f'group ARN \'{cw_lg_arn}\'')
        return [processed_arn, cw_lg_arn]

    def _extract_arns(self, output: dict) -> list:
        arns = []
        _LOG.info(f'Extracting and processing arns from output')
        for arn, meta in output.items():
            resource_type = meta['resource_meta']['resource_type']
            if resource_type in [SWAGGER_UI_TYPE]:
                continue
            processor_func = self.resource_type_to_preprocessor_mapping.get(
                resource_type)
            if processor_func:
                arn = processor_func(arn, meta)
            if isinstance(arn, list):
                arns.extend(arn)
            else:
                arns.append(arn)
        return arns

    def apply_tags(self, output: dict):
        failed_arns = []
        for tags, res_group in self._group_output_by_tags(output):
            arns = self._extract_arns(res_group)
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self.connection.tag_resources, batch,
                                    tags) for batch in chunks(arns, 20)
                ]
                for future in as_completed(futures):
                    failed = future.result()
                    if failed:
                        failed_arns.extend(failed.keys())
        if not failed_arns:
            _LOG.info(f'Tags were successfully applied.')
        else:
            USER_LOG.warn(f'Can\'t apply tags for resources: '
                          f'{failed_arns}')

    def remove_tags(self, output: dict):
        failed_arns = []
        for tags, res_group in self._group_output_by_tags(output):
            arns = self._extract_arns(res_group)
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        self.connection.untag_resources, batch,
                        list(tags.keys())) for batch in chunks(arns, 20)
                ]
                for future in as_completed(futures):
                    failed = future.result()
                    if failed:
                        failed_arns.extend(failed.keys())
        if not failed_arns:
            USER_LOG.info(f'Tags were successfully removed from all resources')
        else:
            USER_LOG.warn(f'Can\'t remove tags from resources: '
                          f'{failed_arns}')

    def apply_post_deployment_tags(self, output: dict):
        output = {k: v for k, v in output.items() if
                  v['resource_meta']['resource_type'] in
                  self.post_deploy_tagging_types}
        self.apply_tags(output)

    def update_tags(self, old_output: dict, new_output: dict):
        failed_arns = []
        for arn, res_meta in new_output.items():
            arns = []
            res_type = res_meta['resource_meta']['resource_type']
            if res_type in self.untaggable_resource_types:
                continue
            old_res_meta = old_output.get(arn)
            old_res_tags = old_res_meta['resource_meta'].get('tags', {})
            new_res_tags = res_meta['resource_meta'].get('tags', {})
            to_tag = {k: v for k, v in new_res_tags.items()
                      if k not in old_res_tags.keys() or
                      v != old_res_tags.get(k)}
            to_untag = [k for k in old_res_tags.keys()
                        if k not in new_res_tags.keys()]
            preprocess_arn = self.resource_type_to_preprocessor_mapping.get(
                res_type)
            if preprocess_arn:
                arn = preprocess_arn(arn, res_meta)

            if isinstance(arn, list):
                arns.extend(arn)
            else:
                arns.append(arn)

            if to_tag:
                failed_tag = self.connection.tag_resources(arns, to_tag)
                if failed_tag:
                    failed_arns.append(arn)

            if to_untag:
                failed_untag = self.connection.untag_resources(arns, to_untag)
                if failed_untag:
                    failed_arns.append(arn)
            if failed_arns:
                USER_LOG.warn(f'Can\'t update tags for resources '
                              f'{failed_arns}.')
            else:
                _LOG.info('Tags were updated successfully')

    @staticmethod
    def _group_output_by_tags(output: dict) -> list[tuple]:
        result = []
        for res_meta in output.values():
            if res_meta['resource_meta'].get('tags'):
                res_meta['resource_meta']['tags'] = dict(
                    sorted(res_meta['resource_meta']['tags'].items()))

        tags_list = [v['resource_meta']['tags'] for v in
                     output.values() if v['resource_meta'].get('tags')]
        tags_ids = set([frozenset(tags.items()) for tags in tags_list])

        for tags_id in tags_ids:
            for tags in tags_list:
                if tags_id == frozenset(tags.items()):
                    res_tags = tags
                    break
            res_group = {k: v for k, v in output.items() if
                         tags_id == frozenset(
                             v['resource_meta'].get('tags', {}).items())}
            result.append((res_tags, res_group))
        return result
