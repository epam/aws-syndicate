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

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import dict_keys_to_upper_camel_case
from syndicate.core.resources.batch_compenv_resource import \
    (DEFAULT_STATE,
     DEFAULT_SERVICE_ROLE)
from .cf_iam_role_converter import CfIamRoleConverter
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_helper import to_logic_name, iam_role_logic_name

_LOG = get_logger('syndicate.core.transform.cloudformation'
                  '.converter.cf_batch_compenv_converter')


class CfBatchComputeEnvironmentConverter(CfResourceConverter):

    def convert(self, name, meta):
        comp_env = batch.ComputeEnvironment(to_logic_name(name))

        meta['compute_environment_name'] = name

        state = meta.get('state')
        if not state:
            state = DEFAULT_STATE

        service_role = meta.get('service_role')
        if not service_role:
            role = self.get_resource(iam_role_logic_name(DEFAULT_SERVICE_ROLE))

            if not role:
                _LOG.warn("Default Service Role '%s' not found "
                          "and will be to the template.", DEFAULT_SERVICE_ROLE)
                iam_conn = self.resources_provider.iam().iam_conn
                allowed_account = iam_conn.resource.CurrentUser().arn.split(':')[4]
                role_converter = CfIamRoleConverter(
                    template=self.template,
                    config=self.config,
                    resources_provider=self.resources_provider)

                role_converter.convert(DEFAULT_SERVICE_ROLE, {
                    'allowed_accounts': allowed_account,
                    'principal_service': 'batch'
                })

                policy = self.get_resource(to_logic_name(DEFAULT_SERVICE_ROLE))
                CfIamRoleConverter.attach_managed_policy(role=role, policy=policy)
            service_role = DEFAULT_SERVICE_ROLE
        role = self.get_resource(iam_role_logic_name(service_role))
        if not role:
            raise AssertionError("IAM role '{}' is not present "
                                 "in build meta.".format(service_role))
        compute_resources = meta.get('compute_resources')
        if compute_resources:
            tags = compute_resources.get('tags', {}).copy()
            compute_resources = dict_keys_to_upper_camel_case(compute_resources)
            if tags:
                compute_resources['Tags'] = tags
            comp_env.ComputeResources = batch.ComputeResources.from_dict(
                title=None, d=compute_resources)

        comp_env.Type = meta['compute_environment_type']
        comp_env.ServiceRole = role.get_att('Arn')
        comp_env.ComputeEnvironmentName = name
        comp_env.State = state
        self.template.add_resource(comp_env)
