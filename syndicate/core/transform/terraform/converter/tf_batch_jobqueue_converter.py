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
from syndicate.core.resources.batch_jobqueue_resource import DEFAULT_STATE
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_com_env_arn


class BatchJobQueueEnvConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        state = resource.get('state')
        if not state:
            state = DEFAULT_STATE
        priority = resource.get('priority')
        compute_order = resource.get('compute_environment_order', [])
        batch_queue_env = job_queue(name=name, state=state, priority=priority,
                                    compute_environment_order=compute_order)
        self.template.add_aws_batch_job_queue(meta=batch_queue_env)


def job_queue(name, state, priority, compute_environment_order):
    params = {
        'name': name,
        'state': state,
        'priority': priority
    }

    com_env_order = []
    compute_environment_order.sort(key=lambda o: o['order'], reverse=False)
    for order_def in compute_environment_order:
        compute_env = order_def['compute_environment']
        com_env_order.append(build_com_env_arn(com_env_name=compute_env))

    if com_env_order:
        params['compute_environments'] = com_env_order

    resource = {
        name: params
    }
    return resource
