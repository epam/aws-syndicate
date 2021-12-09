from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import API_GATEWAY_TYPE


class ApiGatewayGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = API_GATEWAY_TYPE
    REQUIRED_RAPAMS = ['deploy_stage', ]
    NOT_REQUIRED_DEFAULTS = {
        'dependencies': list,
        'resources': dict,
        'minimum_compression_size': None
    }

    def _resolve_not_required_configuration(self) -> dict:
        result = super()._resolve_not_required_configuration()
        example_resource = {
            "/example": {
                "GET": {
                    "enable_cors": True,
                    "authorization_type": "NONE",
                    "integration_type": "mock"
                }
            }
        }
        result['resources'].update(example_resource)
        return result
