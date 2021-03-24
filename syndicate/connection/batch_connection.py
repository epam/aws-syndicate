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

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

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

    def create_compute_environment(self, compute_environment_name, compute_environment_type, state, service_role=None,
                                   compute_resource_type=None, allocation_strategy=None, min_vcpus=None, max_vcpus=None,
                                   desired_vcpus=None, instance_types=None, image_id=None, subnets=None,
                                   security_group_ids=None, ec2_keypair=None, instance_role=None, placement_group=None,
                                   bid_percentage=None, spot_iam_fleet_role=None, launch_template_id=None,
                                   launch_template_name=None, launch_template_version=None, ec2_configuration=None):
        params = dict(computeEnvironmentName=compute_environment_name)

        available_env_types = ('MANAGED', 'UNMANAGED')
        if compute_environment_type not in available_env_types:
            raise AssertionError(
                'Compute environment type must be one of the following: {0}'.format(available_env_types)
            )
        params['type'] = compute_environment_type

        available_states = ('ENABLED', 'DISABLED')
        if state not in available_states:
            raise AssertionError(
                'Compute environment state must be one of the following: {0}'.format(available_states)
            )
        params['state'] = state

        if service_role:
            # todo service role validation
            params['serviceRole'] = service_role

        if params['type'] == 'MANAGED':
            compute_resource = dict()
            available_compute_resource_types = ('EC2', 'SPOT', 'FARGATE', 'FARGATE_SPOT')
            if compute_resource_type not in available_compute_resource_types:
                raise AssertionError(
                    'Compute resource type must be one of the following: {0}'.format(available_compute_resource_types)
                )
            compute_resource['type'] = compute_resource_type

            if allocation_strategy:
                available_allocation_strategies = ('BEST_FIT', 'BEST_FIT_PROGRESSIVE', 'SPOT_CAPACITY_OPTIMIZED')
                if allocation_strategy not in available_allocation_strategies:
                    raise AssertionError(
                        'Compute resource allocation strategy must be one of the following: {0}'.format(
                            available_allocation_strategies)
                    )
                compute_resource['allocationStrategy'] = allocation_strategy

            if not max_vcpus:
                raise AssertionError(
                    'Missing required maxvCpus value'
                )
            compute_resource['maxvCpus'] = max_vcpus

            if min_vcpus:
                if min_vcpus > max_vcpus:
                    raise AssertionError(
                        'MinvCpus must be less or equal to MaxvCpus'
                    )
                compute_resource['minvCpus'] = min_vcpus

            if desired_vcpus:
                if desired_vcpus > max_vcpus:
                    raise AssertionError("desiredvCpus must be smaller than MaxvCpus")
                if min_vcpus and desired_vcpus < min_vcpus:
                    raise AssertionError("desiredvCpus must be greater than MinvCpus")

                compute_resource['desiredvCpus'] = desired_vcpus

            if instance_types:
                # todo instance type validation
                compute_resource['instanceTypes'] = instance_types

            if image_id:
                # todo image id validation
                compute_resource['imageId'] = image_id

            if subnets:
                # todo subnets validation
                compute_resource['subnets'] = subnets

            if security_group_ids:
                # todo security group ids validation:
                compute_resource['securityGroupIds'] = security_group_ids

            if ec2_keypair:
                # todo keypair validation
                compute_resource['ec2KeyPair'] = ec2_keypair

            if instance_role:
                # todo instance role validation
                compute_resource['instanceRole'] = instance_role

            if placement_group:
                # todo placement group validation
                compute_resource['placementGroup'] = placement_group

            if bid_percentage:
                if compute_resource['type'] in ('FARGATE', 'FARGATE_SPOT'):
                    raise AssertionError(
                        "Specifying spot big percentage is not applicable for Fargate resources"
                    )

                if not 0 < bid_percentage < 100:
                    raise AssertionError("bidPercentage must be between 0 and 100")
                compute_resource['bidPercentage'] = bid_percentage
            if spot_iam_fleet_role:
                if compute_resource.get('type') == 'SPOT':
                    # todo spot iam fleet role validation
                    compute_resource['spotIamFleetRole'] = spot_iam_fleet_role

            # may specify id or name, but not both
            if launch_template_id or launch_template_name:
                template = dict()
                if launch_template_id:
                    template['launchTemplateId'] = launch_template_id
                elif launch_template_name:
                    template['launchTemplateName'] = launch_template_name

                if launch_template_version:
                    template['version'] = launch_template_version
                compute_resource['launchTemplate'] = template

            if ec2_configuration:
                if compute_resource['type'] in ('FARGATE', 'FARGATE_SPOT'):
                    raise AssertionError(
                        "Specifying EC2 Configuration is not applicable for Fargate resources"
                    )
                # todo ec2 configuration validation
                compute_resource['ec2Configuration'] = ec2_configuration
            params['computeResources'] = compute_resource
        return self.client.create_compute_environment(**params)

    def update_compute_environment(self, compute_environment, state=None, compute_resources=None, service_role=None):
        params = dict(computeEnvironment=compute_environment)

        if state:
            params['state'] = state

        if compute_resources:
            params['computeResources'] = compute_resources

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
        return self.client.delete_compute_environment(computeEnvironment=compute_environment)

    def create_job_queue(self, job_queue_name, state, priority, compute_environment_order, tags=None):
        params = dict(jobQueueName=job_queue_name)

        available_states = ('ENABLED', 'DISABLED')
        if state not in available_states:
            raise AssertionError(
                'Job queue state must be one of the following: {0}'.format(
                    available_states)
            )
        params['state'] = state

        if not 0 < priority < 1000:
            raise AssertionError(
                "Job queue priority must be between 0 and 1000"
            )
        params['priority'] = priority

        params['computeEnvironmentOrder'] = list()
        for compute_environment in compute_environment_order:
            order = compute_environment.get('order', None)
            compute_environment_name = compute_environment.get('compute_environment', None)

            if order and compute_environment_name:
                item = dict(order=order, computeEnvironment=compute_environment_name)
                params['computeEnvironmentOrder'].append(item)
        if not params['computeEnvironmentOrder']:
            raise AssertionError('computeEnvironmentOrder parameter is required')
        if tags:
            params['tags'] = tags
        return self.client.create_job_queue(**params)

    def describe_job_queue(self, job_queues=None, max_results=None, next_token=None):
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

    def update_job_queue(self, job_queue, state=None, priority=None, compute_environment_order=None):
        params = dict(jobQueue=job_queue)

        available_states = ('ENABLED', 'DISABLED')
        if state:
            if state not in available_states:
                raise AssertionError(
                    'Job queue state must be one of the following: {0}'.format(
                        available_states)
                )
            params['state'] = state

        if priority:
            if not 0 < priority < 1000:
                raise AssertionError(
                    "Job queue priority must be between 0 and 1000"
                )
            params['priority'] = priority

        if compute_environment_order or isinstance(compute_environment_order, list):
            params['computeEnvironmentOrder'] = compute_environment_order

        return self.client.update_job_queue(**params)

    def delete_job_queue(self, job_queue):
        return self.client.delete_job_queue(
            jobQueue=job_queue
        )

    def register_job_definition(self, job_definition_name, job_definition_type, parameters=None,
                                container_properties=None, node_properties=None, retry_strategy=None,
                                propagate_tags=None,
                                timeout=None, tags=None, platform_capabilities=None):

        params = dict(jobDefinitionName=job_definition_name)

        available_job_def_types = ('container', 'multinode')
        if job_definition_type not in available_job_def_types:
            raise AssertionError(
                'Job definition type must be one of the following: {0}'.format(
                    available_job_def_types)
            )
        params['type'] = job_definition_type

        if container_properties:
            # todo container properties validation
            params['containerProperties'] = container_properties

        if node_properties:
            # todo node_properties_validation
            params['nodeProperties'] = node_properties

        if parameters:
            params['parameters'] = parameters

        if params['type'] == 'container' and not container_properties and not node_properties:
            raise AssertionError(
                "Specifying container properties or node properties is required for the 'container' job definition type"
            )

        if retry_strategy:
            params['retryStrategy'] = retry_strategy

        if propagate_tags:
            params['propagateTags'] = propagate_tags

        if timeout:
            params['timeout'] = timeout

        if tags:
            params['tags'] = tags

        available_platform_capabilities = ('EC2', 'FARGATE')
        if platform_capabilities:
            if platform_capabilities not in available_platform_capabilities:
                raise AssertionError(
                    'Platform capabilities must be one of the following: {0}'.format(
                        available_platform_capabilities)
                )
            params['platformCapabilities'] = platform_capabilities

        return self.client.register_job_definition(**params)

    def describe_job_definition(self, job_definition):
        return self.client.describe_job_definitions(jobDefinitionName=job_definition)

    def deregister_job_definition(self, job_definition_name):
        job_definition = '{0}:{1}'.format(job_definition_name,
                                          self._get_job_def_last_revision_number(job_definition_name))
        return self.client.deregister_job_definition(
            jobDefinition=job_definition
        )

    def _get_job_def_last_revision_number(self, job_definition_name):
        job_definition = self.describe_job_definition(job_definition=job_definition_name)['jobDefinitions'][-1]
        return job_definition['revision']
