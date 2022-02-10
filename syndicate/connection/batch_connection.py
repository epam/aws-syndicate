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

from boto3 import client
from botocore.waiter import WaiterModel, create_waiter_with_client

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.helper import dict_keys_to_camel_case

_LOG = get_logger('syndicate.connection.batch_connection')


@apply_methods_decorator(retry)
class BatchConnection(object):
    """ AWS Batch connection class. """

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('batch', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Batch connection.')

    def create_compute_environment(self, compute_environment_name,
                                   compute_environment_type, state,
                                   service_role=None,
                                   compute_resources=None):
        params = dict(
            computeEnvironmentName=compute_environment_name,
            type=compute_environment_type,
            state=state,
            serviceRole=service_role,
        )

        if compute_resources:
            compute_resources = dict_keys_to_camel_case(compute_resources)
            params['computeResources'] = compute_resources

        return self.client.create_compute_environment(**params)

    def update_compute_environment(self, compute_environment, state=None,
                                   compute_resources=None, service_role=None):
        params = dict(computeEnvironment=compute_environment)

        if state:
            params['state'] = state

        if compute_resources:
            params['computeResources'] = dict_keys_to_camel_case(
                compute_resources)

        if service_role:
            params['serviceRole'] = service_role

        return self.client.update_compute_environment(**params)

    def describe_compute_environments(self, compute_environments):
        params = dict()
        if isinstance(compute_environments, str):
            params['computeEnvironments'] = [compute_environments]

        if isinstance(compute_environments, list):
            params['computeEnvironments'] = compute_environments
        return self.client.describe_compute_environments(**params)

    def delete_compute_environment(self, compute_environment):
        return self.client.delete_compute_environment(
            computeEnvironment=compute_environment)

    def create_job_queue(self, job_queue_name, state, priority,
                         compute_environment_order, tags=None):
        params = dict(
            jobQueueName=job_queue_name,
            state=state,
            priority=priority,
        )

        for index, item in enumerate(compute_environment_order):
            compute_environment_order[index] = dict_keys_to_camel_case(item)
        params['computeEnvironmentOrder'] = compute_environment_order

        return self.client.create_job_queue(**params)

    def describe_job_queue(self, job_queues=None, max_results=None,
                           next_token=None):
        params = dict()
        if not job_queues:
            params['jobQueues'] = []
        if isinstance(job_queues, str):
            params['jobQueues'] = [job_queues]
        if isinstance(job_queues, list):
            params['jobQueues'] = job_queues

        if max_results:
            params['maxResults'] = max_results
        if next_token:
            params['nextToken'] = next_token

        return self.client.describe_job_queues(**params)

    def update_job_queue(self, job_queue, state=None, priority=None,
                         compute_environment_order=None):
        params = dict(jobQueue=job_queue)

        if state:
            params['state'] = state

        if priority:
            params['priority'] = priority

        if compute_environment_order:
            params['computeEnvironmentOrder'] = compute_environment_order

        return self.client.update_job_queue(**params)

    def delete_job_queue(self, job_queue):
        return self.client.delete_job_queue(
            jobQueue=job_queue
        )

    def register_job_definition(self, job_definition_name, job_definition_type,
                                parameters=None,
                                container_properties=None,
                                node_properties=None, retry_strategy=None,
                                propagate_tags=None,
                                timeout=None, tags=None,
                                platform_capabilities=None):

        params = dict(
            jobDefinitionName=job_definition_name,
            type=job_definition_type,
        )
        if parameters:
            params['parameters'] = dict_keys_to_camel_case(parameters)

        if container_properties:
            params['containerProperties'] = dict_keys_to_camel_case(
                container_properties)

        if node_properties:
            params['nodeProperties'] = dict_keys_to_camel_case(node_properties)

        if retry_strategy:
            params['retryStrategy'] = dict_keys_to_camel_case(retry_strategy)

        if propagate_tags is not None:
            params['propagateTags'] = propagate_tags
        if timeout:
            params['timeout'] = dict_keys_to_camel_case(timeout)
        if tags:
            params['tags'] = tags

        if platform_capabilities:
            params['platformCapabilities'] = platform_capabilities

        return self.client.register_job_definition(**params)

    def describe_job_definition(self, job_definition, max_results=None,
                                status=None):
        params = dict(jobDefinitionName=job_definition)
        if max_results:
            params['maxResults'] = max_results
        if status:
            params['status'] = status
        return self.client.describe_job_definitions(**params)

    def deregister_job_definition(self, job_definition_name):
        revisions = self._get_job_def_revisions(
            job_definition_name=job_definition_name)

        for revision in revisions:
            job_definition = '{0}:{1}'.format(job_definition_name, revision)
            self.client.deregister_job_definition(
                jobDefinition=job_definition
            )

    def get_compute_environment_waiter(self):
        waiter_id = 'ComputeEnvironmentWaiter'
        model = WaiterModel({
            'version': 2,
            'waiters': {
                waiter_id: {
                    'delay': 2,
                    'operation': 'DescribeComputeEnvironments',
                    'maxAttempts': 10,
                    'acceptors': [
                        {
                            'expected': 'VALID',
                            'matcher': 'pathAll',
                            'state': 'success',
                            'argument': 'computeEnvironments[].status'
                        },
                        {
                            'expected': 'INVALID',
                            'matcher': 'pathAny',
                            'state': 'failure',
                            'argument': 'computeEnvironments[].status'
                        }
                    ]
                }
            }
        })
        return create_waiter_with_client(waiter_id, model, self.client)

    def get_job_queue_waiter(self):
        waiter_id = 'JobQueueWaiter'
        model = WaiterModel({
            'version': 2,
            'waiters': {
                waiter_id: {
                    'delay': 1,
                    'operation': 'DescribeJobQueues',
                    'maxAttempts': 10,
                    'acceptors': [
                        {
                            'expected': 'VALID',
                            'matcher': 'pathAll',
                            'state': 'success',
                            'argument': 'jobQueues[].status'
                        },
                        {
                            'expected': 'INVALID',
                            'matcher': 'pathAny',
                            'state': 'failure',
                            'argument': 'jobQueues[].status'
                        }
                    ]
                }
            }
        })
        return create_waiter_with_client(waiter_id, model, self.client)

    def _get_job_def_revisions(self, job_definition_name):
        job_definition_data = self.describe_job_definition(
            job_definition=job_definition_name)
        revisions = []
        for job_def in job_definition_data['jobDefinitions']:
            if job_def.get('status') == 'ACTIVE':
                revisions.append(job_def.get('revision'))
        return revisions
