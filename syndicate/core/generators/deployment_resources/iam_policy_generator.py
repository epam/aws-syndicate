from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import IAM_POLICY


class IAMPolicyGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = IAM_POLICY
    CONFIGURATION = {
        "policy_content": dict
    }

    def _resolve_configuration(self, defaults_dict=None) -> dict:
        result = super()._resolve_configuration()
        if not result['policy_content']:
            example_resource = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "*",
                        "Effect": "Deny",
                        "Resource": "*"
                    }
                ]
            }
            result['policy_content'].update(example_resource)
        return result
