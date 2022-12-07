import time

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs, \
    dict_keys_to_capitalized_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.firehose_resource')


class FirehoseResource(BaseResource):

    def __init__(self, firehose_conn) -> None:
        self.connection = firehose_conn

    def create_stream(self, args):
        return self.create_pool(self._create_stream_from_meta, args)

    @unpack_kwargs
    def _create_stream_from_meta(self, name, meta):
        response = self.connection.describe_delivery_stream(name)
        if response:
            stream_status = response['DeliveryStreamStatus']['StreamStatus']
            if stream_status == 'DELETING':
                _LOG.debug(f'Waiting for deletion kinesis stream {name}...')
                time.sleep(75)
            else:
                _LOG.warn(f'{name} kinesis stream exists')
                return build_description_obj(response, name, meta)

        s3_configuration = dict_keys_to_capitalized_camel_case(
            meta['s3_destination_configuration'])
        s3_configuration['RoleARN'] = s3_configuration.pop('RoleArn')
        s3_configuration['BucketARN'] = s3_configuration.pop('BucketArn')
        stream_type = meta['stream_type']
        kinesis_stream_source = meta.get('kinesis_stream_source')
        if kinesis_stream_source:
            kinesis_stream_source = dict_keys_to_capitalized_camel_case(
                kinesis_stream_source)
            kinesis_stream_source['KinesisStreamARN'] = kinesis_stream_source.pop(
                'KinesisStreamArn')
            kinesis_stream_source['RoleARN'] = kinesis_stream_source.pop(
                'RoleArn')

        self.connection.create_delivery_stream(
            stream_name=name, s3_configuration=s3_configuration,
            stream_type=stream_type,
            kinesis_stream_source=kinesis_stream_source)
        _LOG.info(f'Created firehose stream {name}')
        return self.describe_stream(name=name, meta=meta)

    def describe_stream(self, name, meta):
        response = self.connection.describe_delivery_stream(name)
        return build_description_obj(response, name, meta)

    def delete_stream(self, name):
        response = self.connection.delete_delivery_stream(name)
        return response
