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
from troposphere import batch

from syndicate.core.helper import dict_keys_to_upper_camel_case
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, iam_role_logic_name


class CfBatchJobDefinitionConverter(CfResourceConverter):

    def convert(self, name, meta):
        container_props = meta.get('container_properties')
        if container_props:
            container_props = self.prepare_container_properties(
                container_props=container_props,
                job_definition_name=name)

        logic_name = to_logic_name('BatchJobDefinition', name)
        job_def = batch.JobDefinition(logic_name)
        job_def.JobDefinitionName = name
        job_def.Type = meta['job_definition_type']

        if meta.get('parameters'):
            job_def.Parameters = meta['parameters']

        if container_props:
            job_def.ContainerProperties = batch.ContainerProperties.from_dict(
                title=None, d=container_props)

        node_props = meta.get('node_properties')
        if node_props:
            container_props = \
                node_props.get('node_range_properties', {}).get('container')
            if container_props:
                container_props = self.prepare_container_properties(
                    container_props=container_props,
                    job_definition_name=name)
                del(node_props['node_range_properties']['container'])

            node_props = dict_keys_to_upper_camel_case(node_props)
            if container_props:
                node_props['node_range_properties']['container'] = \
                    container_props
            job_def.NodeProperties = batch.NodeProperties.from_dict(
                title=None, d=node_props)

        if meta.get('retry_strategy'):
            retry_strategy = dict_keys_to_upper_camel_case(
                meta['retry_strategy'])
            job_def.RetryStrategy = batch.RetryStrategy.from_dict(
                title=None, d=retry_strategy)

        if meta.get('propagate_tags') is not None:
            job_def.PropagateTags = meta['propagate_tags']
        if meta.get('timeout'):
            timeout = dict_keys_to_upper_camel_case(meta['timeout'])
            job_def.Timeout = batch.Timeout.from_dict(title=None, d=timeout)
        if meta.get('tags'):
            job_def.Tags = meta['tags']
        if meta.get('platform_capabilities'):
            job_def.PlatformCapabilities = meta['platform_capabilities']
        self.template.add_resource(job_def)

    def prepare_container_properties(self, container_props,
                                     job_definition_name):
        job_role_arn = container_props.get('job_role_arn')
        execution_role_arn = container_props.get('execution_role_arn')
        log_conf_options = container_props \
            .get('log_configuration', {}).get('options', {}).copy()
        container_props = dict_keys_to_upper_camel_case(container_props)
        if job_role_arn:
            container_props['JobRoleArn'] = \
                self.check_role_exists(job_role_arn, job_definition_name)
        if execution_role_arn:
            container_props['ExecutionRoleArn'] = \
                self.check_role_exists(execution_role_arn, job_definition_name)
        if log_conf_options:
            container_props['log_configuration']['options'] = \
                log_conf_options
        return container_props

    def check_role_exists(self, role_arn, job_definition_name):
        role = self.get_resource(iam_role_logic_name(role_arn))
        if role:
            return role.get_att('Arn')
        iam_conn = self.resources_provider.iam().iam_conn
        existing_role = iam_conn.check_if_role_exists(role_name=role_arn)
        if existing_role:
            return existing_role
        raise AssertionError(
            'IAM Role "{}" specified in "{}" batch job definition '
            'does not exist'.format(role_arn, job_definition_name))
