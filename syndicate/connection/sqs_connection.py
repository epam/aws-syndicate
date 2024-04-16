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
import json

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.sqs_connection')
FIFO_REGIONS = ['us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1']


@apply_methods_decorator(retry())
class SqsConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('sqs', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new SQS connection.')

    def create_queue(self, queue_name, delay_seconds=None,
                     maximum_message_size=None, message_retention_period=None,
                     policy=None, receive_message_wait_time_seconds=None,
                     redrive_policy=None, visibility_timeout=None,
                     kms_master_key_id=None,
                     kms_data_key_reuse_period_seconds=None, fifo_queue=False,
                     content_based_deduplication=None):
        attributes = dict()
        if fifo_queue:
            if self.region not in FIFO_REGIONS:
                raise AssertionError(
                    'FIFO queue is not supported for {0} region.'
                    ' Available in : {1}'.format(self.region, FIFO_REGIONS))
            attributes['FifoQueue'] = str(fifo_queue)
        params = dict(QueueName=queue_name)
        if delay_seconds:
            if delay_seconds < 0 or delay_seconds > 900:
                raise AssertionError(
                    'Delay seconds for queue must be between 0 and 900 seconds')
            attributes['DelaySeconds'] = str(delay_seconds)
        if maximum_message_size:
            if maximum_message_size < 1024 or maximum_message_size > 262144:
                raise AssertionError(
                    'Maximum message size must be between 1024 and 262144 bytes')
            attributes['MaximumMessageSize'] = str(maximum_message_size)
        if message_retention_period:
            if message_retention_period < 60 or message_retention_period > 1209600:
                raise AssertionError(
                    'Message retention size must be between 60 and 1209600 seconds')
            attributes['MessageRetentionPeriod'] = str(
                message_retention_period)
        if policy:
            if isinstance(policy, dict):
                policy = json.dumps(policy)
            attributes['Policy'] = policy
        if receive_message_wait_time_seconds:
            if receive_message_wait_time_seconds < 0 or receive_message_wait_time_seconds > 20:
                raise AssertionError(
                    'Receive message wait time must be between 0 and 20 seconds')
            attributes[
                'ReceiveMessageWaitTimeSeconds'] = str(
                receive_message_wait_time_seconds)
        if redrive_policy:
            attributes['RedrivePolicy'] = json.dumps(redrive_policy)
        if visibility_timeout:
            if visibility_timeout < 0 or visibility_timeout > 43200:
                raise AssertionError(
                    'Visibility timeout must be between 0 and 43200 seconds')
            attributes['VisibilityTimeout'] = str(visibility_timeout)
        if kms_master_key_id:
            attributes['KmsMasterKeyId'] = kms_master_key_id
        if kms_data_key_reuse_period_seconds:
            if kms_data_key_reuse_period_seconds < 60 or kms_data_key_reuse_period_seconds > 86400:
                raise AssertionError(
                    'KMS key reuse period must be between 60 and 86400 seconds')
            attributes[
                'KmsDataKeyReusePeriodSeconds'] = str(
                kms_data_key_reuse_period_seconds)
        if content_based_deduplication:
            attributes[
                'ContentBasedDeduplication'] = str(content_based_deduplication)
        params['Attributes'] = attributes
        return self.client.create_queue(**params)

    def delete_queue(self, queue_url):
        self.client.delete_queue(QueueUrl=queue_url)

    def list_queues(self, url_prefix):
        response = self.client.list_queues(QueueNamePrefix=url_prefix)
        return response.get('QueueUrls', list())

    def get_queue_url(self, queue_name, account_id):
        try:
            response = self.client.get_queue_url(QueueName=queue_name,
                                                 QueueOwnerAWSAccountId=account_id)
            return response['QueueUrl']
        except ClientError as e:
            if 'AWS.SimpleQueueService.NonExistentQueue' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_queue_attributes(self, queue_url, attribute_names=None):
        if attribute_names is None:
            attribute_names = ['All']
        try:
            return self.client.get_queue_attributes(QueueUrl=queue_url,
                                                    AttributeNames=attribute_names)
        except ClientError as e:
            if 'QueueDoesNotExistException' in str(e):
                pass  # valid exception
            else:
                raise e
