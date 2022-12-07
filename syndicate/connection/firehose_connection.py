from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.firehose_connection')


@apply_methods_decorator(retry)
class FirehoseConnection(object):
    """ Firehose connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('firehose', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Firehose connection.')

    def create_delivery_stream(self, stream_name, stream_type,
                               s3_configuration, kinesis_stream_source=None):
        params = {'DeliveryStreamName': stream_name,
                  'S3DestinationConfiguration': s3_configuration,
                  'DeliveryStreamType': stream_type}
        if kinesis_stream_source:
            params['KinesisStreamSourceConfiguration'] = kinesis_stream_source
        return self.client.create_delivery_stream(**params)['DeliveryStreamARN']

    def describe_delivery_stream(self, stream_name, limit=None,
                                 exclusive_start_id=None):
        params = {'DeliveryStreamName': stream_name}
        if limit:
            params['Limit'] = limit
        if exclusive_start_id:
            params['ExclusiveStartDestinationId'] = exclusive_start_id

        try:
            return self.client.describe_delivery_stream(**params)[
                    'DeliveryStreamDescription']
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                _LOG.warning(
                    f'Cannot find delivery stream with name {stream_name}')
                pass
            else:
                raise e

    def delete_delivery_stream(self, stream_name):
        try:
            return self.client.delete_delivery_stream(
                DeliveryStreamName=stream_name)
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                _LOG.warning(
                    f'Cannot find delivery stream with name {stream_name}')
                pass
            else:
                raise e
