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
        s3_configuration = dict_keys_to_capitalized_camel_case(
            meta['s3_destination_configuration'])
        s3_configuration['RoleARN'] = s3_configuration.pop('RoleArn')
        s3_configuration['BucketARN'] = s3_configuration.pop('BucketArn')
        stream_type = meta['stream_type']
        self.connection.create_delivery_stream(
            stream_name=name, s3_configuration=s3_configuration,
            stream_type=stream_type)
        _LOG.info(f'Created firehose stream {name}')
        return self.describe_stream(name=name, meta=meta)

    def describe_stream(self, name, meta):
        response = self.connection.describe_delivery_stream(name)
        return build_description_obj(response, name, meta)

    def delete_stream(self, name):
        response = self.connection.delete_delivery_stream(name)
        return response
