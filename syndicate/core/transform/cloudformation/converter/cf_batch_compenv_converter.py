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
from ..cf_transform_utils import (iam_role_logic_name,
                                  iam_instance_profile_logic_name,
                                  batch_compute_env_logic_name)

_LOG = get_logger('cf_batch_compenv_converter')


class CfBatchComputeEnvironmentConverter(CfResourceConverter):

    def convert(self, name, meta):
        logic_name = batch_compute_env_logic_name(name)
        comp_env = batch.ComputeEnvironment(logic_name)

        state = meta.get('state')
        if not state:
            state = DEFAULT_STATE

        iam_conn = self.resources_provider.iam().iam_conn
        role_name = meta.get('service_role')
        if not role_name:
            role_name = DEFAULT_SERVICE_ROLE
            default_role = iam_conn.get_role(role_name=role_name)
            if not default_role:
                default_role = self.get_resource(iam_role_logic_name(role_name))

            if not default_role:
                _LOG.warn("Default Service Role '%s' not found "
                          "and will be added to the template.", role_name)
                allowed_account = iam_conn.resource.CurrentUser().arn.split(':')[4]
                role_converter = CfIamRoleConverter(
                    template=self.template,
                    config=self.config,
                    resources_provider=self.resources_provider)

                role_converter.convert(role_name, {
                    'allowed_accounts': allowed_account,
                    'principal_service': 'batch'
                })
                default_role = self.get_resource(iam_role_logic_name(role_name))
                policy = iam_conn.get_policy_arn(role_name)
                if not policy:
                    raise AssertionError(
                        'IAM Policy "{}" does not exist'.format(role_name))
                CfIamRoleConverter.attach_managed_policy(role=default_role,
                                                         policy=policy)

        role = iam_conn.check_if_role_exists(role_name=role_name)
        if not role:
            role = self.get_resource(iam_role_logic_name(role_name))
            if not role:
                raise AssertionError('IAM role "{}" does not exist.'
                                     .format(role_name))
            comp_env.ServiceRole = role.get_att('Arn')
        else:
            comp_env.ServiceRole = role

        compute_res = meta.get('compute_resources')
        if compute_res:
            tags = compute_res.get('tags', {}).copy()
            instance_role = compute_res.get('instance_role')
            compute_res = dict_keys_to_upper_camel_case(compute_res)
            if tags:
                compute_res['Tags'] = tags
            if instance_role:
                instance_profile = self.get_resource(
                    iam_instance_profile_logic_name(instance_role))
                if instance_profile:
                    compute_res['InstanceRole'] = instance_profile.ref()
            comp_env.ComputeResources = batch.ComputeResources.from_dict(
                title=None, d=compute_res)

        comp_env.Type = meta['compute_environment_type']
        comp_env.ComputeEnvironmentName = name
        comp_env.State = state
        self.template.add_resource(comp_env)
