from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import SNS_PLATFORM_APPLICATION_TYPE


class SNSApplicationGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = SNS_PLATFORM_APPLICATION_TYPE
    CONFIGURATION = {
        "platform": None,
        "region": None,
        "attributes": dict
    }

    def __init__(self, **kwargs):
        self.attributes = []
        if 'attributes' in kwargs:
            self.attributes.extend(kwargs.pop('attributes'))
        super().__init__(**kwargs)

    def _resolve_configuration(self, defaults_dict=None) -> dict:
        result = super()._resolve_configuration()
        for attr_name, attr_value in self.attributes:
            result['attributes'][attr_name] = attr_value
        return result
