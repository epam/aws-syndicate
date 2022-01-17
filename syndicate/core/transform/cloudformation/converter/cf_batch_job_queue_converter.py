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

from syndicate.core.resources.batch_jobqueue_resource import DEFAULT_STATE
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, batch_compute_env_logic_name


class CfBatchJobQueueConverter(CfResourceConverter):

    def convert(self, name, meta):
        logic_name = to_logic_name('BatchJobQueue', name)

        comp_env_order = meta['compute_environment_order']
        for index, item in enumerate(comp_env_order):
            comp_env = self.get_resource(batch_compute_env_logic_name(
                compute_env_name=item['compute_environment']))
            comp_env_order[index] = batch.ComputeEnvironmentOrder(
                ComputeEnvironment=comp_env.ref(),
                Order=item['order']
            )

        queue = batch.JobQueue(
            title=logic_name,
            JobQueueName=name,
            State=meta.get('state', DEFAULT_STATE),
            Priority=meta['priority'],
            ComputeEnvironmentOrder=comp_env_order
        )
        if meta.get('tags'):
            queue.Tags = meta['tags']

        self.template.add_resource(queue)
