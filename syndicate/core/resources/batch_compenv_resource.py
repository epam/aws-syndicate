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
from botocore.waiter import WaiterError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.batch_compenv')

DEFAULT_STATE = 'ENABLED'
DEFAULT_SERVICE_ROLE = 'AWSBatchServiceRole'


class BatchComputeEnvironmentResource(BaseResource):

    def __init__(self, batch_conn, iam_conn, region, account_id):
        self.batch_conn = batch_conn
        self.iam_conn = iam_conn
        self.region = region
        self.account_id = account_id

    def create_compute_environment(self, args):
        return self.create_pool(self._create_compute_environment_from_meta,
                                args)

    def describe_compute_environment(self, name, meta):
        response = self.batch_conn.describe_compute_environments(name)

        try:
            arn = response['computeEnvironments'][0]['computeEnvironmentArn']
            return {arn: build_description_obj(response, name, meta)}
        except (KeyError, IndexError):
            _LOG.warn("Batch Compute Environment %s not found", name)
            return {}

    def remove_compute_environment(self, args):
        self.create_pool(self._remove_compute_environment, args)

    @unpack_kwargs
    def _remove_compute_environment(self, arn, config):
        compute_environment_data = self.batch_conn.describe_compute_environments(arn)
        try:
            compute_environment_data = compute_environment_data[
                'computeEnvironments'][0]
        except (KeyError, IndexError):
            _LOG.warn("Batch Compute Environment %s not found", config[
                'resource_name'])
            return
        if compute_environment_data['state'] == 'ENABLED':
            # need to disable compute env first
            self.batch_conn.update_compute_environment(arn, state='DISABLED')

        self.batch_conn.delete_compute_environment(compute_environment=arn)

        compute_environment_name = compute_environment_data[
            'computeEnvironmentName']
        _LOG.info('Batch Compute Environment %s was removed.',
                  compute_environment_name)

    @unpack_kwargs
    def _create_compute_environment_from_meta(self, name, meta):
        from syndicate.core import CONFIG
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
            role = self.iam_conn.get_role(role_name=DEFAULT_SERVICE_ROLE)
            if not role:
                _LOG.warn("Default Service Role '%s' not found and will be "
                          "created", DEFAULT_SERVICE_ROLE)
                allowed_account = self.account_id
                self.iam_conn.create_custom_role(
                    role_name=DEFAULT_SERVICE_ROLE,
                    allowed_account=allowed_account,
                    allowed_service='batch',
                    permissions_boundary=CONFIG.iam_permissions_boundary
                )
                policy_arn = self.iam_conn.get_policy_arn(DEFAULT_SERVICE_ROLE)
                self.iam_conn.attach_policy(
                    role_name=DEFAULT_SERVICE_ROLE,
                    policy_arn=policy_arn
                )
                _LOG.info("Created default service role %s", DEFAULT_SERVICE_ROLE)
            params['service_role'] = DEFAULT_SERVICE_ROLE

        # resolve IAM Role name with IAM Role ARN
        params['service_role'] = self.iam_conn.check_if_role_exists(
            role_name=params['service_role'])

        self.batch_conn.create_compute_environment(**params)
        try:
            waiter = self.batch_conn.get_compute_environment_waiter()
            waiter.wait(computeEnvironments=[name])
        except WaiterError as e:
            _LOG.error(e)

        _LOG.info('Created Batch Compute Environment %s.', name)
        return self.describe_compute_environment(name, meta)

    def _is_compute_env_exist(self, compute_environment_name):
        response = self.batch_conn.describe_compute_environments(
            compute_environment_name)
        return bool(response['computeEnvironments'])

    def update_compute_environment(self, args):
        return self.create_pool(self._update_compute_environment_from_meta,
                                args)

    def _update_compute_environment_from_meta(self, meta):
        from syndicate.core import CONFIG
        name = meta.pop('name')
        arn = f'arn:aws:batch:{self.region}:{self.account_id}:' \
              f'compute-environment/{name}'
        if not self._is_compute_env_exist(arn):
            raise AssertionError(f'Compute environment \'{name}\' does not '
                                 f'exist')

        params = meta['meta'].copy()
        if 'resource_type' in params:
            del params['resource_type']
        if 'compute_environment_type' in params:
            del params['compute_environment_type']
        if 'subnets' in params:
            del params['subnets']
        if 'compute_resources' in params:
            del params['compute_resources']

        state = params.get('state')
        if state and state != 'ENABLED' and state != 'DISABLED':
            _LOG.warn(f"Invalid state value for compute environment '{arn}': "
                      f"{state}")
            raise AssertionError(f'Invalid state value for compute '
                                 f'environment \'{arn}\': {state}')

        params['compute_environment'] = arn

        service_role = params.get('service_role')
        if not service_role:
            role = self.iam_conn.get_role(role_name=DEFAULT_SERVICE_ROLE)
            if not role:
                _LOG.warn(f"Default Service Role '{DEFAULT_SERVICE_ROLE}' not "
                          f"found and will be created")
                allowed_account = self.account_id
                self.iam_conn.create_custom_role(
                    role_name=DEFAULT_SERVICE_ROLE,
                    allowed_account=allowed_account,
                    allowed_service='batch',
                    permissions_boundary=CONFIG.iam_permissions_boundary
                )
                policy_arn = self.iam_conn.get_policy_arn(DEFAULT_SERVICE_ROLE)
                self.iam_conn.attach_policy(
                    role_name=DEFAULT_SERVICE_ROLE,
                    policy_arn=policy_arn
                )
                _LOG.info(f"Created default service role "
                          f"{DEFAULT_SERVICE_ROLE}")
            params['service_role'] = DEFAULT_SERVICE_ROLE

        # resolve IAM Role name with IAM Role ARN
        params['service_role'] = self.iam_conn.check_if_role_exists(
            role_name=params['service_role'])

        # response: TypedDict[computeEnvironmentName|Arn, ResponseMetadata]
        _response: dict = self.batch_conn.update_compute_environment(**params)
        return self.describe_compute_environment(name=name, meta=meta)
