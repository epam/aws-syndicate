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

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('core.resources.sqs_resource')

AVAILABLE_REGIONS = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2',
                     'ap-south-1', 'ap-northeast-2', 'ap-southeast-1',
                     'ap-southeast-2', 'ap-northeast-1', 'ca-central-1',
                     'eu-central-1', 'eu-west-2', 'sa-east-1', 'eu-west-1']
FIFO_REGIONS = ['us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1']
FIFO_SUFFIX = '.fifo'


class SqsResource(BaseResource):

    def __init__(self, sqs_conn_builder, region, account_id) -> None:
        self.sqs_conn_builder = sqs_conn_builder
        self.region = region
        self.account_id = account_id

    def create_sqs_queue(self, args):
        return self.create_pool(self._create_sqs_queue_from_meta, args)

    def describe_queue(self, queue_url, name, meta, resource_name, region):
        response = self.sqs_conn_builder(region).get_queue_attributes(
            queue_url)
        arn = self._build_queue_arn(resource_name=resource_name, region=region)
        return {arn: build_description_obj(response, name, meta)}

    def describe_queue_from_meta(self, name, meta):
        region = meta.get('region', self.region)
        is_fifo = meta.get('fifo_queue', False)
        resource_name = self.build_resource_name(is_fifo, name)
        queue_url = self.sqs_conn_builder(region).get_queue_url(
            resource_name, self.account_id)
        if not queue_url:
            return {}
        response = self.sqs_conn_builder(region).get_queue_attributes(
            queue_url)
        return {
            self._build_queue_arn(resource_name,
                                  region): build_description_obj(
                response, name, meta)
        }

    def remove_queues(self, args):
        self.create_pool(self._remove_queue, args)
        # wait to remove all queues
        if args:
            time.sleep(60)

    @unpack_kwargs
    def _remove_queue(self, arn, config):
        region = arn.split(':')[3]
        queue_name = config['resource_name']
        resource_meta = config['resource_meta']
        try:
            is_fifo = resource_meta.get('fifo_queue', False)
            resource_name = self.build_resource_name(is_fifo, queue_name)
            queue_url = self.sqs_conn_builder(region).get_queue_url(
                resource_name,
                self.account_id)
            if queue_url:
                self.sqs_conn_builder(region).delete_queue(queue_url)
                _LOG.info('SQS queue %s was removed.', queue_name)
            else:
                _LOG.warn('SQS queue %s is not found', queue_name)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'ResourceNotFoundException':
                _LOG.warn('SQS queue %s is not found', queue_name)
            else:
                raise e

    @unpack_kwargs
    def _create_sqs_queue_from_meta(self, name, meta):
        region = meta.get('region', self.region)
        is_fifo = meta.get('fifo_queue', False)
        resource_name = self.build_resource_name(is_fifo, name)
        queue_url = self.sqs_conn_builder(region).get_queue_url(resource_name,
                                                                self.account_id)
        if queue_url:
            _LOG.warn('SQS queue %s exists.', name)
            return self.describe_queue(queue_url, name, meta, resource_name,
                                       region)
        delay_sec = meta.get('delay_seconds')
        max_mes_size = meta.get('maximum_message_size')
        mes_ret_period = meta.get('message_retention_period')
        policy = meta.get('policy')
        recieve_mes_wait_sec = meta.get('receive_message_wait_time_seconds')
        redrive_policy = meta.get('redrive_policy')
        vis_timeout = meta.get('visibility_timeout')
        kms_master_key_id = meta.get('kms_master_key_id')
        kms_data_reuse_period = meta.get('kms_data_key_reuse_period_seconds')
        if is_fifo and region not in FIFO_REGIONS:
            raise AssertionError('FIFO queue is not available in {0}.'
                                 .format(region))
        content_deduplication = meta.get('content_based_deduplication')
        params = dict(queue_name=resource_name,
                      delay_seconds=delay_sec,
                      maximum_message_size=max_mes_size,
                      message_retention_period=mes_ret_period,
                      policy=policy,
                      receive_message_wait_time_seconds=recieve_mes_wait_sec,
                      redrive_policy=redrive_policy,
                      visibility_timeout=vis_timeout,
                      kms_master_key_id=kms_master_key_id,
                      kms_data_key_reuse_period_seconds=kms_data_reuse_period,
                      fifo_queue=is_fifo,
                      content_based_deduplication=content_deduplication)
        queue_url = self.sqs_conn_builder(region).create_queue(**params)[
            'QueueUrl']
        _LOG.info('Created SQS queue %s.', name)
        return self.describe_queue(queue_url, name, meta, resource_name,
                                   region)

    @staticmethod
    def build_resource_name(is_fifo, name):
        resource_name = name
        if is_fifo and not name.endswith(FIFO_SUFFIX):
            resource_name += FIFO_SUFFIX
        return resource_name

    def _build_queue_arn(self, resource_name, region):
        arn = 'arn:aws:sqs:{0}:{1}:{2}'.format(region, self.account_id,
                                               resource_name)
        return arn
