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
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.kinesis_connection')


@apply_methods_decorator(retry)
class KinesisConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('kinesis', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Kinesis connection.')

    def create_stream(self, stream_name, shard_count):
        if not isinstance(shard_count, int) or shard_count > 25:
            raise TypeError(
                'Shard count must be a valid integer '
                'less than 25 (max value per region). Actual type: {0}'.format(
                    type(shard_count)))
        params = dict(StreamName=stream_name, ShardCount=shard_count)
        return self.client.create_stream(**params)

    def get_stream(self, stream_name):
        try:
            return self.client.describe_stream(StreamName=stream_name)[
                'StreamDescription']
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_list_streams(self):
        result = []
        response = self.client.list_streams()
        do_continue = response.get('HasMoreStreams')
        if 'StreamNames' in response:
            result.extend(response['StreamNames'])
        while do_continue:
            response = self.client.list_streams(
                ExclusiveStartStreamName=result[-1])
            do_continue = response.get('HasMoreStreams')
            if 'StreamNames' in response:
                result.extend(response['StreamNames'])
        return result

    def remove_stream(self, stream_name):
        self.client.delete_stream(StreamName=stream_name)
