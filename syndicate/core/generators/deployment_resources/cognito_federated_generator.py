from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import COGNITO_FEDERATED_POOL_TYPE


class CognitoFederatedPoolGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = COGNITO_FEDERATED_POOL_TYPE
    CONFIGURATION = {
        "auth_role": None,
        "unauth_role": None,
        "open_id_providers": list,
        "provider_name": None,
    }
