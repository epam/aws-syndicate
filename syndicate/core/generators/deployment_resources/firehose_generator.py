from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import FIREHOSE_TYPE

KINESIS_STREAM_FIREHOSE_TYPE = 'KinesisStreamAsSource'


class FirehoseGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = FIREHOSE_TYPE
    CONFIGURATION = {
        'stream_type': str,
        # 'kinesis_stream_source_configuration': dict,
        's3_destination_configuration': {
            'role': str,
            'bucket': str,
            'buffering_hints': {
                'size_in_mbs': 5,
                'interval_in_seconds': 300
            },
            'compression_format': str
        },
        'tags': dict
    }

    def write(self):
        self.CONFIGURATION['s3_destination_configuration'].update(
            {
                'role': self._dict.pop('destination_role'),
                'bucket': self._dict.pop('destination_bucket')
            }
        )

        if self._dict['stream_type'] == KINESIS_STREAM_FIREHOSE_TYPE:
            self.CONFIGURATION['kinesis_stream_source_configuration'] = {
                    'kinesis_stream_arn': self._dict['kinesis_stream_arn'],
                    'role': self._dict['kinesis_stream_role']
                }

        super().write()
