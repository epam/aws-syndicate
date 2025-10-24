from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import RDS_DB_CLUSTER_TYPE, RDS_DB_INSTANCE_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.exceptions import InvalidValueError, ParameterError

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class RDSDBClusterGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = RDS_DB_CLUSTER_TYPE
    CONFIGURATION = {
        'engine': str,
        'engine_version': None,
        'master_username': str,
        'master_user_password': None,
        'database_name': str,
        'port': int,
        'iam_db_auth': None,
        'vpc_security_group_ids': list,
        'availability_zones': None,
        'db_subnet_group_name': None,
        'manage_master_user_password': None,
        'tags': dict
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:

        if not self._dict.get('port'):
            if self._dict['engine'] == 'aurora-postgresql':
                self._dict['port'] = 5432
            else:
                self._dict['port'] = 3306

        self._dict['master_user_password'] = self._dict.pop('master_password')
        self._dict['manage_master_user_password'] = \
            self._dict.pop('manage_master_password', None)

        self._dict['db_subnet_group_name'] = \
            self._dict.pop('db_subnet_group', None)

        if not any((self._dict.get('master_user_password'),
                    self._dict.get('manage_master_user_password'))):
            raise ParameterError(
                "Either 'master_password' or 'manage_master_password' as "
                "`true` must be specified"
            )

        if self._dict.get('master_user_password'):
            self._validate_master_password()

        return super()._generate_resource_configuration()

    def _validate_master_password(self):
        to_validate = self._dict.get('master_user_password')
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


class RDSDBInstanceGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = RDS_DB_INSTANCE_TYPE
    CONFIGURATION = {
        'instance_class': str,
        'engine': str,
        'engine_version': None,
        'cluster_name': None,
        'database_name': None,
        'master_username': None,
        'master_user_password': None,
        'port': None,
        'publicly_accessible': False,
        'vpc_security_group_ids': None,
        'availability_zone': None,
        'tags': dict
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:

        if self._dict.get('master_password'):
            self._validate_master_password()
            self._dict['master_user_password'] = \
                self._dict.pop('master_password')

        if cluster_name := self._dict.get('cluster_name'):
            self._validate_resource_existence(
                resource_name=cluster_name,
                resource_type=RDS_DB_CLUSTER_TYPE)

            deployment_resources = self._get_deployment_resources_file_content(
                self._get_resource_meta_paths(
                    resource_name=cluster_name,
                    resource_type=RDS_DB_CLUSTER_TYPE)[0])

            cluster_config = deployment_resources[cluster_name]
            self._dict['engine'] = cluster_config.get('engine')

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