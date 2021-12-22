from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import KINESIS_STREAM_TYPE


class KinesisStreamGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = KINESIS_STREAM_TYPE
    CONFIGURATION = {
        'shard_count': None,
    }
