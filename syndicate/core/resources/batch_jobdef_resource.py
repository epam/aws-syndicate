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
from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.batch_jobdef')


class BatchJobDefinitionResource(BaseResource):
    def __init__(self, batch_conn):
        self.batch_conn = batch_conn

    def register_job_definition(self, args):
        return self.create_pool(self._register_job_definition_from_meta, args)

    def describe_job_definition(self, name, meta):
        response = self.batch_conn.describe_job_definition(job_definition=name)
        arn = response['jobDefinitions'][-1]['jobDefinitionArn']  # todo handle KeyError
        return {arn: build_description_obj(response, name, meta)}

    def deregister_job_definition(self, args):
        self.create_pool(self._deregister_job_definition, args)

    @unpack_kwargs
    def _register_job_definition_from_meta(self, name, meta):
        params = meta.copy()
        params['job_definition_name'] = name

        if 'resource_type' in params:
            del params['resource_type']

        self.batch_conn.register_job_definition(**params)
        _LOG.info('Created Batch Job Definition %s.', name)
        return self.describe_job_definition(name, meta)

    @unpack_kwargs
    def _deregister_job_definition(self, arn, config):
        job_def_name = config['resource_name']
        return self.batch_conn.deregister_job_definition(job_def_name)
