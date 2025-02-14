from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import FIREHOSE_TYPE

KINESIS_STREAM_FIREHOSE_TYPE = 'KinesisStreamAsSource'


class FirehoseGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = FIREHOSE_TYPE
    CONFIGURATION = {
        'stream_type': str,
        'kinesis_stream_source_configuration': None,
        's3_destination_configuration': dict,
        'tags': dict
    }

    def __init__(self, **kwargs):
        kwargs['s3_destination_configuration'] = {
            'role': kwargs.pop('destination_role'),
            'bucket': kwargs.pop('destination_bucket'),
            'buffering_hints': {
                'size_in_mbs': 5,
                'interval_in_seconds': 300
            },
            'compression_format': kwargs.pop('compression_format')
        }

        if kwargs['stream_type'] == KINESIS_STREAM_FIREHOSE_TYPE:
            kwargs['kinesis_stream_source_configuration'] = {
                'kinesis_stream_arn': kwargs.pop('kinesis_stream_arn'),
                'role': kwargs.pop('kinesis_stream_role')
            }

        super().__init__(**kwargs)
