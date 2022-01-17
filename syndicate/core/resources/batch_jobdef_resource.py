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
    def __init__(self, batch_conn, iam_conn):
        self.batch_conn = batch_conn
        self.iam_conn = iam_conn

    def register_job_definition(self, args):
        return self.create_pool(self._register_job_definition_from_meta, args)

    def describe_job_definition(self, name, meta):
        response = self.batch_conn.describe_job_definition(job_definition=name,
                                                           max_results=1,
                                                           status='ACTIVE')
        try:
            arn = response['jobDefinitions'][-1]['jobDefinitionArn']
            return {arn: build_description_obj(response, name, meta)}
        except (KeyError, IndexError):
            _LOG.warn("Batch Job Definition %s not found", name)
            return {}

    def deregister_job_definition(self, args):
        self.create_pool(self._deregister_job_definition, args)

    @unpack_kwargs
    def _register_job_definition_from_meta(self, name, meta):
        params = meta.copy()
        params['job_definition_name'] = name

        if 'resource_type' in params:
            del params['resource_type']

        container_properties = params.get('container_properties')
        if container_properties:
            job_role_arn = container_properties.get('job_role_arn')
            if job_role_arn:
                params['container_properties']['job_role_arn'] = self.iam_conn.check_if_role_exists(
                    role_name=job_role_arn
                )

            execution_role_arn = container_properties.get('execution_role_arn')
            if execution_role_arn:
                params['container_properties']['execution_role_arn'] = self.iam_conn.check_if_role_exists(
                    role_name=execution_role_arn
                )

        self.batch_conn.register_job_definition(**params)
        _LOG.info('Created Batch Job Definition %s.', name)
        return self.describe_job_definition(name, meta)

    @unpack_kwargs
    def _deregister_job_definition(self, arn, config):
        job_def_name = config['resource_name']
        self.batch_conn.deregister_job_definition(job_def_name)
        _LOG.info('Batch Job Definition %s was removed.', job_def_name)

    @unpack_kwargs
    def _update_job_definition_from_meta(self, name, meta, context):
        """Updates batch job definition. If a user updates job definition,
        the previous active revision should be deregistered """
        response = self.batch_conn.describe_job_definition(job_definition=name,
                                                           max_results=1,
                                                           status='ACTIVE')
        previous_revision = response['jobDefinitions'][-1]['revision']

        self.batch_conn.client.deregister_job_definition(
            jobDefinition=f'{name}:{previous_revision}')
        BatchJobDefinitionResource._register_job_definition_from_meta(
            {
                'self': self,
                'name': name,
                'meta': meta
            }
        )

    def update_job_definition(self, args):
        self.create_pool(self._update_job_definition_from_meta, args)
