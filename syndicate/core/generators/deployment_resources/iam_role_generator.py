from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
import click
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import IAM_ROLE, IAM_POLICY
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.iam_role_generator')
USER_LOG = get_user_logger()


class IAMRoleGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = IAM_ROLE
    CONFIGURATION = {
        "principal_service": None,
        "predefined_policies": list,
        "custom_policies": list,
        "allowed_accounts": list,
        "external_id": None,
        "instance_profile": bool,
        "permissions_boundary": str
    }

    def _resolve_configuration(self, defaults_dict=None) -> dict:
        self.validate_custom_policies_existence()

        if self._dict['principal_service'] == 'ec2' and \
                not self._dict['instance_profile']:
            USER_LOG.info("Setting 'instance_profile' value to 'True' because "
                          "it wasn't specified and principal service is 'ec2'")
            self._dict['instance_profile'] = True
        return super()._resolve_configuration()

    def validate_custom_policies_existence(self):
        custom_policies = set(self._dict.get('custom_policies', []))
        _LOG.info(f"Validating existence of these policies: {custom_policies}")
        available_policies_dict = self._find_resources_by_type(IAM_POLICY)

        available_policies = set()
        for value in available_policies_dict.values():
            available_policies.update(value)

        custom_policies = custom_policies - available_policies
        if custom_policies:
            message = f"Custom policies: {custom_policies} was not found " \
                      f"in deployment resources"
            _LOG.error(f"Validation error: {message}")
            raise ValueError(message)
        _LOG.info(f"Validation successfully finished, policies exist")
