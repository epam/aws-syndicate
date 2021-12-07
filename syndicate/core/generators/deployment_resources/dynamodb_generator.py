from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import DYNAMO_TABLE_TYPE

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.dynamodb_table')
USER_LOG = get_user_logger()


class DynamoDBGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DYNAMO_TABLE_TYPE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hash_key_name = kwargs.get('hash_key_name')
        self.hash_key_type = kwargs.get('hash_key_type')

    def _generate_resource_configuration(self) -> dict:
        configuration = super()._generate_resource_configuration()

        configuration.update({
            'hash_key_name': self.hash_key_name,
            'hash_key_type': self.hash_key_type
        })
        return configuration