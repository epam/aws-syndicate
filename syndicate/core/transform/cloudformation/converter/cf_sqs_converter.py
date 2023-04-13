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
from troposphere import sqs, GetAtt

from syndicate.core.resources.sqs_resource import FIFO_REGIONS, SqsResource
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, sqs_queue_logic_name


class CfSqsConverter(CfResourceConverter):

    def convert(self, name, meta):
        is_fifo = bool(meta.get('fifo_queue', False))
        queue_name = SqsResource.build_resource_name(is_fifo, name)

        delay_sec = meta.get('delay_seconds')
        max_mes_size = meta.get('maximum_message_size')
        mes_ret_period = meta.get('message_retention_period')
        policy = meta.get('policy')
        receive_mes_wait_sec = meta.get('receive_message_wait_time_seconds')
        redrive_policy = meta.get('redrive_policy')
        vis_timeout = meta.get('visibility_timeout')
        kms_master_key_id = meta.get('kms_master_key_id')
        kms_data_reuse_period = meta.get('kms_data_key_reuse_period_seconds')
        content_deduplication = bool(meta.get('content_based_deduplication',
                                              False))

        region = meta.get('region', self.config.region)
        if is_fifo and region not in FIFO_REGIONS:
            raise AssertionError('FIFO queue is not available in {0}.'
                                 .format(region))

        queue = sqs.Queue(sqs_queue_logic_name(name))
        queue.QueueName = queue_name
        self.template.add_resource(queue)

        if delay_sec:
            if delay_sec < 0 or delay_sec > 900:
                raise AssertionError(
                    'Delay seconds for queue must be '
                    'between 0 and 900 seconds')
            queue.DelaySeconds = delay_sec

        if max_mes_size:
            if max_mes_size < 1024 or max_mes_size > 262144:
                raise AssertionError(
                    'Maximum message size must be '
                    'between 1024 and 262144 bytes')
            queue.MaximumMessageSize = max_mes_size

        if mes_ret_period:
            if mes_ret_period < 60 or mes_ret_period > 1209600:
                raise AssertionError(
                    'Message retention size must be '
                    'between 60 and 1209600 seconds')
            queue.MessageRetentionPeriod = mes_ret_period

        if receive_mes_wait_sec:
            if receive_mes_wait_sec < 0 or receive_mes_wait_sec > 20:
                raise AssertionError(
                    'Receive message wait time must be '
                    'between 0 and 20 seconds')
            queue.ReceiveMessageWaitTimeSeconds = receive_mes_wait_sec

        if redrive_policy:
            queue.RedrivePolicy = sqs.RedrivePolicy(
                deadLetterTargetArn=redrive_policy['deadLetterTargetArn'],
                maxReceiveCount=redrive_policy['maxReceiveCount']
            )

        if vis_timeout:
            if vis_timeout < 0 or vis_timeout > 43200:
                raise AssertionError(
                    'Visibility timeout must be '
                    'between 0 and 43200 seconds')
            queue.VisibilityTimeout = vis_timeout

        if kms_master_key_id:
            queue.KmsMasterKeyId = kms_master_key_id

        if kms_data_reuse_period:
            if kms_data_reuse_period < 60 or kms_data_reuse_period > 86400:
                raise AssertionError(
                    'KMS key reuse period must be '
                    'between 60 and 86400 seconds')
            queue.KmsDataKeyReusePeriodSeconds = kms_data_reuse_period

        if is_fifo:
            queue.FifoQueue = True

        if content_deduplication:
            queue.ContentBasedDeduplication = True

        if policy:
            queue_policy = sqs.QueuePolicy(
                to_logic_name('SQSQueuePolicy', name))
            queue_policy.PolicyDocument = policy
            queue_policy.Queues = [queue.ref()]
            self.template.add_resource(queue_policy)
