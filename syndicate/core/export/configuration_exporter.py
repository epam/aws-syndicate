"""
    Copyright 2024 EPAM Systems, Inc.

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
import os
from abc import ABC, abstractmethod

from syndicate.commons import deep_get
from syndicate.commons.log_helper import get_user_logger
from syndicate.core.constants import EXPORT_DIR_NAME
from syndicate.core.helper import build_path

USER_LOG = get_user_logger()


class ConfigurationExporter(ABC):

    def __init__(self):
        from syndicate.core import CONFIG, RESOURCES_PROVIDER
        self.config = CONFIG
        self.project_path = self.config.project_path
        self.resources_provider = RESOURCES_PROVIDER

    def prepare_output_directory(self, output_dir):
        if not output_dir:
            output_dir_path = build_path(
                self.project_path, EXPORT_DIR_NAME)
        elif not os.path.isabs(output_dir):
            output_dir_path = build_path(
                os.getcwd(), output_dir)
        else:
            output_dir_path = output_dir
        os.makedirs(output_dir_path, exist_ok=True)
        return output_dir_path

    @staticmethod
    def _remove_prefix_suffix_from_string(string: str,
                                          prefix: str,
                                          suffix: str) -> str:
        if string.startswith(prefix):
            string = string[len(prefix):]
        if string.endswith(suffix):
            string = string[:-len(suffix)]
        return string

    @abstractmethod
    def export_configuration(self, *args, **kwargs):
        pass


class OASV3Exporter(ConfigurationExporter):

    def __init__(self):
        super().__init__()
        self.extended_prefix_mode = self.config.extended_prefix_mode
        self.prefix = self.config.resources_prefix
        self.suffix = self.config.resources_suffix

    def export_configuration(self, arn, meta):
        return self._export_api_gw_openapi_spec(arn, meta)

    def _export_api_gw_openapi_spec(self, api_arn: str,
                                    meta: dict) -> (str, dict):
        api_id = api_arn.split('/')[-1]
        api_stage = deep_get(meta, ['resource_meta', 'deploy_stage'])
        specification = self.resources_provider.api_gw().describe_openapi(
            api_id=api_id,
            stage_name=api_stage)
        if not specification:
            USER_LOG.warn(f'API Gateway not found by the ARN: "{api_arn}"')
            return api_id, None
        if self.extended_prefix_mode:
            specification['info']['title'] = (
                self._remove_prefix_suffix_from_string(
                    specification['info']['title'],
                    self.prefix,
                    self.suffix))
            self._remove_prefix_suffix_from_arn(
                specification,
                self.prefix,
                self.suffix)
        return api_id, specification

    def _remove_prefix_suffix_from_arn(self, spec: dict, prefix: str,
                                       suffix: str) -> None:
        def __remove_prefix_suffix(string: str, delimiter: str) -> str:
            if delimiter in string:
                origin_parts = string.split(delimiter)
                new_parts = []
                for part in origin_parts:
                    new_parts.append(
                        self._remove_prefix_suffix_from_string(
                            part, prefix, suffix))
                string = delimiter.join(new_parts)
            return string

        if isinstance(spec, dict):
            for key in spec.keys():
                if isinstance(spec[key], dict):
                    self._remove_prefix_suffix_from_arn(spec[key],
                                                        prefix, suffix)
                else:
                    if isinstance(spec[key], str):
                        if 'arn' in spec[key]:
                            spec[key] = __remove_prefix_suffix(spec[key], ':')
                            spec[key] = __remove_prefix_suffix(spec[key], '/')
