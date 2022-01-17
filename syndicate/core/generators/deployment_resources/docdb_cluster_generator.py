from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import DOCUMENTDB_CLUSTER_TYPE
from syndicate.commons.log_helper import get_logger, get_user_logger

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.documentdb_cluster')
USER_LOG = get_user_logger()


class DocumentDBClusterGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DOCUMENTDB_CLUSTER_TYPE
    CONFIGURATION = {
        "vpc_security_group_ids": list,
        "availability_zones": list,
        "port": 27017,
        "master_username": None,
        "master_password": None,
    }

    def _generate_resource_configuration(self) -> dict:
        self._validate_master_password()
        return super()._generate_resource_configuration()

    def _validate_master_password(self):
        to_validate = self._dict.get('master_password')
        _LOG.info(f"Validating master password '{to_validate}'...")
        error = None
        if not 8 <= len(to_validate) <= 100:
            error = "master password must contain from 8 to 100 characters"
        elif any(char in to_validate for char in ('"@/')):
            error = 'master password cannot contain forward slash (/), ' \
                    'double quote (") or the "at" symbol (@)'
        if error:
            _LOG.error(f"Validation error: {error}")
            raise ValueError(error)
        _LOG.info("Master password validation passed successfully")
