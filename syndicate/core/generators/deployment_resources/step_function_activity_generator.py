from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import STATE_ACTIVITY_TYPE


class StepFunctionActivityGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = STATE_ACTIVITY_TYPE
