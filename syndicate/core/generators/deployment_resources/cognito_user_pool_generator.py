from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import COGNITO_USER_POOL_TYPE


class CognitoUserPoolGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = COGNITO_USER_POOL_TYPE
    CONFIGURATION = {
        "region": None,  # taking his time
        "password_policy": {
            "minimum_length": 8,
            "require_uppercase": True,
            "require_symbols": True,
            "require_lowercase": True,
            "require_numbers": True,
        },
        "auto_verified_attributes": list,
        "sms_configuration": {
            "sns_caller_arn": None,
            "external_id": None
        },
        "username_attributes": list,
        "custom_attributes": list,
        "client": dict
    }

    def __init__(self, **kwargs):
        self.custom_attributes = kwargs.pop('custom_attributes') or []
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        result = super()._generate_resource_configuration()
        for name, attr_type in self.custom_attributes:
            result['custom_attributes'].append({'name': name,
                                                'type': attr_type})
        return result
