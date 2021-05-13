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
from botocore.exceptions import WaiterError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.batch_jobqueue')

DEFAULT_STATE = 'ENABLED'


class BatchJobQueueResource(BaseResource):
    def __init__(self, batch_conn):
        self.batch_conn = batch_conn

    def create_job_queue(self, args):
        return self.create_pool(self._create_job_queue_from_meta, args)

    def describe_job_queue(self, name, meta):
        response = self.batch_conn.describe_job_queue(name)
        try:
            arn = response['jobQueues'][0]['jobQueueArn']
            return {arn: build_description_obj(response, name, meta)}
        except (KeyError, IndexError):
            _LOG.warn("Batch Job Queue %s not found", name)
            return {}

    def remove_job_queue(self, args):
        self.create_pool(self._remove_job_queue, args)

    @unpack_kwargs
    def _remove_job_queue(self, arn, config):
        job_queue_name = config.get('resource_name')

        self.batch_conn.update_job_queue(
            job_queue=arn,
            state='DISABLED',
            compute_environment_order=[]
        )
        self.batch_conn.delete_job_queue(job_queue=arn)
        _LOG.info('Batch Job Queue %s was removed.', job_queue_name)

    @unpack_kwargs
    def _create_job_queue_from_meta(self, name, meta):
        params = meta.copy()
        params['job_queue_name'] = name
        if 'resource_type' in params:
            del params['resource_type']

        if self._is_job_queue_exist(name):
            _LOG.warn('Batch Job Queue %s already exists', name)
            return self.describe_job_queue(name, meta)

        state = params.get('state')
        if not state:
            params['state'] = DEFAULT_STATE

        self.batch_conn.create_job_queue(**params)
        try:
            waiter = self.batch_conn.get_job_queue_waiter()
            waiter.wait(jobQueues=[name])
        except WaiterError as e:
            _LOG.error(e)

        _LOG.info('Created Batch Job Queue %s.', name)
        return self.describe_job_queue(name, meta)

    def _is_job_queue_exist(self, job_queue_name):
        response = self.batch_conn.describe_job_queue(
            job_queues=job_queue_name
        )
        return bool(response['jobQueues'])
