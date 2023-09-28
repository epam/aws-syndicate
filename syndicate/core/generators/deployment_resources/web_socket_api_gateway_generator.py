from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import WEB_SOCKET_API_GATEWAY_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class WebSocketApiGatewayGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = WEB_SOCKET_API_GATEWAY_TYPE
    CONFIGURATION = {
        'deploy_stage': None,
        'route_selection_expression': 'request.body.action',
        'resources': {
            "$connect": {
                "integration_type": "lambda",
                "enable_proxy": True,
                "lambda_alias": "${lambdas_alias_name}",
                "lambda_name": str
            },
            "$disconnect": {
                "integration_type": "lambda",
                "enable_proxy": True,
                "lambda_alias": "${lambdas_alias_name}",
                "lambda_name": str
            },
            "$default": {
                "integration_type": "lambda",
                "enable_proxy": True,
                "lambda_alias": "${lambdas_alias_name}",
                "lambda_name": str
            },
            "example": {
                "integration_type": "lambda",
                "enable_proxy": True,
                "lambda_alias": "${lambdas_alias_name}",
                "lambda_name": str
            }
        },
    }
