from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs, delete_none
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.firehose_resource')


class FirehoseResource(BaseResource):

    def __init__(self, firehose_conn, s3_resource, iam_resource) -> None:
        self.connection = firehose_conn
        self.s3_resource = s3_resource
        self.iam_resource = iam_resource

    def create_stream(self, args):
        return self.create_pool(self._create_stream_from_meta, args)

    @unpack_kwargs
    def _create_stream_from_meta(self, name, meta):
        response = self.connection.describe_delivery_stream(name)
        if response:
            _arn = response['DeliveryStreamARN']
            return self.describe_stream(name, meta, _arn, response)

        _s3 = meta.get('s3_destination_configuration') or {}
        s3_configuration = delete_none({
            'RoleARN': self.iam_resource.build_role_arn(_s3.get('role')),
            'BucketARN': self.s3_resource.build_bucket_arn(_s3.get('bucket')),
            'Prefix': _s3.get('prefix'),
            'ErrorOutputPrefix': _s3.get('error_output_prefix'),
            'BufferingHints': {
                'SizeInMBs': (_s3.get('buffering_hints') or {}).get('size_in_mbs') or 5,
                'IntervalInSeconds': (_s3.get('buffering_hints') or {}).get('interval_in_seconds') or 300
            },
            'CompressionFormat': _s3.get('compression_format') or 'UNCOMPRESSED',
            # 'EncryptionConfiguration': {},
            # 'CloudWatchLoggingOptions': {}
        })
        _kinesis = meta.get('kinesis_stream_source_configuration') or {}
        kinesis_configuration = delete_none({
            'KinesisStreamARN': _kinesis.get('kinesis_stream_arn'),
            'RoleARN': self.iam_resource.build_role_arn(_kinesis.get('role'))
        })
        stream_type = meta.get('stream_type') or 'DirectPut'
        arn = self.connection.create_delivery_stream(
            stream_name=name, s3_configuration=s3_configuration,
            stream_type=stream_type,
            kinesis_stream_source=kinesis_configuration)
        _LOG.info(f'Created firehose stream {arn}')
        return self.describe_stream(name=name, meta=meta, arn=arn)

    def describe_stream(self, name, meta, arn, response: dict = None):
        if not response:
            response = self.connection.describe_delivery_stream(name)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def delete_streams(self, args):
        return self.create_pool(self._delete_stream, args)

    @unpack_kwargs
    def _delete_stream(self, arn, config):
        name = config['resource_name']
        response = self.connection.delete_delivery_stream(name)
        return response
