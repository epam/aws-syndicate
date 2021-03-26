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

        arn = response['jobQueues'][0]['jobQueueArn']  # todo handle KeyError
        return {arn: build_description_obj(response, name, meta)}

    def remove_job_queue(self, args):
        self.create_pool(self._remove_job_queue, args)

    def _remove_job_queue(self, config):
        arn = config['arn']

        self.batch_conn.update_job_queue(
            job_queue=arn,
            state='DISABLED',
            compute_environment_order=[]
        )
        self.batch_conn.delete_job_queue(job_queue=arn)

    @unpack_kwargs
    def _create_job_queue_from_meta(self, name, meta):
        params = meta.copy()
        params['job_queue_name'] = name
        if 'resource_type' in params:
            del params['resource_type']

        if self._is_job_queue_exist(name):
            raise AssertionError(
                'AWS Batch Job Queue with the given name already exists'
            )

        state = params.get('state')
        if not state:
            params['state'] = DEFAULT_STATE

        self.batch_conn.create_job_queue(**params)
        _LOG.info('Created Batch Job Queue %s.', name)
        return self.describe_job_queue(name, meta)

    def _is_job_queue_exist(self, job_queue_name):
        response = self.batch_conn.describe_job_queue(
            job_queues=job_queue_name
        )
        return bool(response['jobQueues'])
