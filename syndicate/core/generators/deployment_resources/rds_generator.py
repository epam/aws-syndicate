from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import RDS_AURORA_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.exceptions import InvalidValueError

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class RDSAuroraGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = RDS_AURORA_TYPE
    CONFIGURATION = {
        'engine': str,
        'engine_version': None,
        'master_username': str,
        'master_user_password': str,
        'database_name': str,
        'port': int,
        'vpc_security_group_ids': list,
        'availability_zones': list,
        'db_instance_config': dict,
        'tags': dict
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        self._validate_master_password()
        if not self._dict.get('port'):
            if self._dict['engine'] == 'aurora-postgresql':
                self._dict['port'] = 5432
            else:
                self._dict['port'] = 3306

        self._dict['master_user_password'] = self._dict.pop('master_password')

        self._dict['db_instance_config'] = {
            'd_b_instance_identifier': self._dict.pop('db_instance_name'),
            'd_b_instance_class': self._dict.pop('db_instance_class'),
            'engine': self._dict['engine'],
            'publicly_accessible': self._dict.pop('publicly_accessible')
        }

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
            raise InvalidValueError(error)
        _LOG.info("Master password validation passed successfully")
