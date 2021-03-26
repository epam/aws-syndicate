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
import time

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.batch_compenv')

DEFAULT_STATE = 'ENABLED'
DEFAULT_SERVICE_ROLE = 'AWSServiceRoleForBatch'


class BatchComputeEnvironmentResource(BaseResource):

    def __init__(self, batch_conn, iam_conn):
        self.batch_conn = batch_conn
        self.iam_conn = iam_conn

    def create_compute_environment(self, args):
        return self.create_pool(self._create_compute_environment_from_meta, args)

    def describe_compute_environment(self, name, meta):
        response = self.batch_conn.describe_compute_environments(name)

        arn = response['computeEnvironments'][0]['computeEnvironmentArn'] # todo handle KeyError
        return {arn: build_description_obj(response, name, meta)}

    def remove_compute_environment(self, args):
        self.create_pool(self._remove_compute_environment, args)

    @unpack_kwargs
    def _remove_compute_environment(self, arn, config):
        compute_environment_data = self.batch_conn.describe_compute_environments(arn)
        compute_environment_data = compute_environment_data['computeEnvironments'][0]  # todo handle KeyError
        if compute_environment_data['state'] == 'ENABLED':
            # need to disable compute env first
            self.batch_conn.update_compute_environment(arn, state='DISABLED')

        return self.batch_conn.delete_compute_environment(compute_environment=arn)

    @unpack_kwargs
    def _create_compute_environment_from_meta(self, name, meta):
        params = meta.copy()
        params['compute_environment_name'] = name

        if 'resource_type' in params:
            del params['resource_type']
        if self._is_compute_env_exist(name):
            _LOG.warn(f'AWS Batch Compute Environment with the name {name} '
                      f'already exists')
            return self.describe_compute_environment(name, meta)

        state = params.get('state')
        if not state:
            params['state'] = DEFAULT_STATE

        service_role = params.get('service_role')
        if not service_role:
            params['service_role'] = DEFAULT_SERVICE_ROLE

        # resolve IAM Role name with IAM Role ARN
        params['service_role'] = self.iam_conn.check_if_role_exists(
            role_name=params['service_role'])
        self.batch_conn.create_compute_environment(**params)

        _LOG.info('Created Batch Compute Environment %s.', name)
        time.sleep(7)
        return self.describe_compute_environment(name, meta)

    def _is_compute_env_exist(self, compute_environment_name):
        response = self.batch_conn.describe_compute_environments(compute_environment_name)
        return bool(response['computeEnvironments'])
