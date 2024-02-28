from syndicate.core.constants import SWAGGER_UI_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator


class SwaggerUIGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = SWAGGER_UI_TYPE
    CONFIGURATION = {
        'path_to_spec': str,
        'target_bucket': str
    }

