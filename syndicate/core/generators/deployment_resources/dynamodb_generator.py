from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import DYNAMO_TABLE_TYPE


class DynamoDBGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DYNAMO_TABLE_TYPE
    REQUIRED_RAPAMS = ['hash_key_name', 'hash_key_type']
    NOT_REQUIRED_DEFAULTS = {
        'sort_key_name': None,
        'sort_key_type': None,
        'read_capacity': 1,
        'write_capacity': 1,
        'global_indexes': list,
        'autoscaling': list
    }
