from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import SNS_TOPIC_TYPE


class SNSTopicGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = SNS_TOPIC_TYPE
    REQUIRED_RAPAMS = ['region']
    NOT_REQUIRED_DEFAULTS = {
        "event_sources": list
    }