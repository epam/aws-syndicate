from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import SNS_TOPIC_TYPE


class SNSTopicGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = SNS_TOPIC_TYPE
    CONFIGURATION = {
        'region': None,
        "event_sources": list
    }
