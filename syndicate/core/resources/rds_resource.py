import copy

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.rds_connection import RDSConnection
from syndicate.core.helper import unpack_kwargs, dict_keys_to_upper_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params, \
    build_description_obj, validate_known_params
from syndicate.exceptions import ResourceNotFoundError

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

CLUSTER_REQUIRED_PARAMS = ['engine']

DB_INSTANCE_REQUIRED_PARAMS = [
    'instance_class',
    'engine'
]

DEPLOY_CLUSTER_KNOWN_PARAMS = [
    'availability_zones',
    'backup_retention_period',
    'character_set_name',
    'database_name',
    'd_b_cluster_parameter_group_name',
    'vpc_security_group_ids',
    'db_subnet_group_name',
    'engine',
    'engine_version',
    'port',
    'master_username',
    'master_user_password',
    'option_group_name',
    'preferred_backup_window',
    'preferred_maintenance_window',
    'replication_source_identifier',
    'tags',
    'storage_encrypted',
    'kms_key_id',
    'pre_signed_url',
    'iam_db_auth',
    'backtrack_window',
    'enable_cloudwatch_logs_exports',
    'engine_mode',
    'scaling_configuration',
    'deletion_protection',
    'global_cluster_identifier',
    'enable_http_endpoint',
    'copy_tags_to_snapshot',
    'domain',
    'domain_i_a_m_role_name',
    'enable_global_write_forwarding',
    'd_b_cluster_instance_class',
    'allocated_storage',
    'storage_type',
    'iops',
    'publicly_accessible',
    'auto_minor_version_upgrade',
    'monitoring_interval',
    'monitoring_role_arn',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'serverless_v2_scaling_configuration',
    'network_type',
    'd_b_system_id',
    'manage_master_user_password',
    'master_user_secret_kms_key_id',
    'source_region'
]

UPDATE_CLUSTER_KNOWN_PARAMS = [
    'new_d_b_cluster_identifier',
    'apply_immediately',
    'backup_retention_period',
    'd_b_cluster_parameter_group_name',
    'vpc_security_group_ids',
    'port',
    'master_user_password',
    'option_group_name',
    'preferred_backup_window',
    'preferred_maintenance_window',
    'iam_db_auth',
    'backtrack_window',
    'cloudwatch_logs_export_configuration',
    'engine_version',
    'allow_major_version_upgrade',
    'd_b_instance_parameter_group_name',
    'domain',
    'domain_i_a_m_role_name',
    'scaling_configuration',
    'deletion_protection',
    'enable_http_endpoint',
    'copy_tags_to_snapshot',
    'enable_global_write_forwarding',
    'd_b_cluster_instance_class',
    'allocated_storage',
    'storage_type',
    'iops',
    'auto_minor_version_upgrade',
    'monitoring_interval',
    'monitoring_role_arn',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'serverless_v2_scaling_configuration',
    'network_type',
    'manage_master_user_password',
    'rotate_master_user_password',
    'master_user_secret_kms_key_id'
]

DEPLOY_DB_INSTANCE_KNOWN_PARAMS = [
    'database_name',
    'allocated_storage',
    'instance_class',
    'engine',
    'master_username',
    'master_user_password',
    'd_b_security_groups',
    'vpc_security_group_ids',
    'availability_zone',
    'db_subnet_group_name',
    'preferred_maintenance_window',
    'd_b_parameter_group_name',
    'backup_retention_period',
    'preferred_maintenance_window',
    'd_b_parameter_group_name',
    'preferred_backup_window',
    'port',
    'multi_a_z',
    'engine_version',
    'auto_minor_version_upgrade',
    'license_model',
    'iops',
    'option_group_name',
    'character_set_name',
    'nchar_character_set_name',
    'publicly_accessible',
    'tags',
    'cluster_name',
    'storage_type',
    'tde_credential_arn',
    'tde_credential_password',
    'storage_encrypted',
    'kms_key_id',
    'domain',
    'copy_tags_to_snapshot',
    'monitoring_interval',
    'monitoring_role_arn',
    'domain_i_a_m_role_name',
    'promotion_tier',
    'timezone',
    'iam_db_auth',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'enable_cloudwatch_logs_exports',
    'processor_features',
    'deletion_protection',
    'max_allocated_storage',
    'enable_customer_owned_ip',
    'custom_iam_instance_profile',
    'backup_target',
    'network_type',
    'storage_throughput',
    'manage_master_user_password',
    'master_user_secret_kms_key_id',
    'c_a_certificate_identifier'
]

UPDATE_DB_INSTANCE_KNOWN_PARAMS = [
    'allocated_storage',
    'instance_class',
    'db_subnet_group_name',
    'd_b_security_groups',
    'vpc_security_group_ids',
    'apply_immediately',
    'master_user_password',
    'd_b_parameter_group_name',
    'backup_retention_period',
    'preferred_backup_window',
    'preferred_maintenance_window',
    'multi_a_z',
    'engine_version',
    'allow_major_version_upgrade',
    'auto_minor_version_upgrade',
    'license_model',
    'iops',
    'option_group_name',
    'storage_type',
    'tde_credential_arn',
    'tde_credential_password',
    'c_a_certificate_identifier',
    'domain',
    'copy_tags_to_snapshot',
    'monitoring_interval',
    'd_b_port_number',
    'publicly_accessible',
    'monitoring_role_arn',
    'domain_i_a_m_role_name',
    'promotion_tier',
    'iam_db_auth',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'cloudwatch_logs_export_configuration',
    'processor_features',
    'use_default_processor_features',
    'deletion_protection',
    'max_allocated_storage',
    'certificate_rotation_restart',
    'replica_mode',
    'enable_customer_owned_ip',
    'aws_backup_recovery_point_arn',
    'automation_mode',
    'resume_full_automation_mode_minutes',
    'network_type',
    'storage_throughput',
    'manage_master_user_password',
    'rotate_master_user_password',
    'master_user_secret_kms_key_id'
]

UPDATE_CLUSTER_NOT_SUPPORTED_KEYS = [
    'resource_type',
    'engine',
    'master_username',
    'database_name',
    'availability_zones',
    'db_subnet_group_name'
]

UPDATE_INSTANCE_NOT_SUPPORTED_KEYS = [
    'engine',
    'cluster_name',
    'resource_type'
]


class RDSDBClusterResource(BaseResource):

    def __init__(self, rds_conn: RDSConnection) -> None:
        self.rds_conn = rds_conn

    def create_db_cluster(self, args: list) -> dict | tuple:
        """ Create RDS cluster in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_db_cluster_from_meta, args, 1)

    @unpack_kwargs
    def _create_db_cluster_from_meta(self, name: str, meta: dict) -> dict:
        """ Create RDS cluster from meta description.

        :type name: str
        :type meta: dict
        """

        validate_params(name, meta, CLUSTER_REQUIRED_PARAMS)

        description = self.rds_conn.get_db_cluster_description(name)
        if description:
            _LOG.warning(f'RDS cluster {name} already exists.')
            return self.describe_db_cluster(
                name=name, meta=meta, description=description)

        params = copy.deepcopy(meta)
        params.pop('resource_type')

        validate_known_params(name, list(params.keys()),
                              DEPLOY_CLUSTER_KNOWN_PARAMS)

        db_subnet_group_name = params.pop('db_subnet_group_name', None)
        iam_db_auth = params.pop('iam_db_auth', None)

        params = dict_keys_to_upper_camel_case(params)

        if db_subnet_group_name is not None:
            params['DBSubnetGroupName'] = db_subnet_group_name

        if iam_db_auth is not None:
            params['EnableIAMDatabaseAuthentication'] = iam_db_auth

        description = self.rds_conn.create_db_cluster(
            name=name,
            params=params
        )

        USER_LOG.info(
            f"Waiting for the DB cluster '{name}' to become available...")
        waiter = self.rds_conn.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )

        USER_LOG.info(f'Endpoint: {description["Endpoint"]}')
        USER_LOG.info(
            f'Reader endpoint: {description["ReaderEndpoint"]}')
        if description.get('CustomEndpoints'):
            endpoints = '\n'.join(description['CustomEndpoints'])
            USER_LOG.info(f'Custom endpoints: {endpoints}')

        return self.describe_db_cluster(
            name=name,
            meta=meta,
            description=description
        )

    def update_db_cluster(self, args: list) -> dict | tuple:
        return self.create_pool(self._update_db_cluster, args, 1)

    @unpack_kwargs
    def _update_db_cluster(self, name: str, meta: dict, context) -> dict:
        cluster = self.rds_conn.get_db_cluster_description(name)
        if not cluster:
            raise ResourceNotFoundError(
                f"RDS DB cluster '{name}' does not exist."
            )

        params = copy.deepcopy(meta)

        # TODO implement tags updating
        params.pop('tags', None)

        for key in UPDATE_CLUSTER_NOT_SUPPORTED_KEYS:
            params.pop(key, None)

        validate_known_params(name, list(params.keys()),
                              UPDATE_CLUSTER_KNOWN_PARAMS)

        db_subnet_group_name = params.pop('db_subnet_group_name', None)
        iam_db_auth = params.pop('iam_db_auth', None)

        params = dict_keys_to_upper_camel_case(params)

        if db_subnet_group_name is not None:
            params['DBSubnetGroupName'] = db_subnet_group_name

        if iam_db_auth is not None:
            params['EnableIAMDatabaseAuthentication'] = iam_db_auth

        params['DBClusterIdentifier'] = name

        description = self.rds_conn.update_db_cluster(
            params=params
        )

        USER_LOG.info(f'Endpoint: {description["Endpoint"]}')
        USER_LOG.info(
            f'Reader endpoint: {description["ReaderEndpoint"]}')
        if description.get('CustomEndpoints'):
            endpoints = '\n'.join(description['CustomEndpoints'])
            USER_LOG.info(f'Custom endpoints: {endpoints}')

        _LOG.info(f"RDS DB cluster '{name}' updated successfully")

        return self.describe_db_cluster(
            name=name,
            meta=meta,
            description=description
        )

    def describe_db_cluster(self, name: str, meta: dict,
                            description: dict = None) -> dict:
        if not description:
            description = self.rds_conn.get_db_cluster_description(name)
            if not description:
                return {}

        arn = description['DBClusterArn']

        return {
            arn: build_description_obj(description, name, meta)
        }

    def remove_db_cluster(self, args: list) -> dict | tuple:
        return self.create_pool(self._remove_db_cluster, args)

    @unpack_kwargs
    def _remove_db_cluster(self, arn: str, config: dict) -> dict:
        from click import confirm as click_confirm

        cluster_name = config['resource_name']
        USER_LOG.info(f"Deleting RDS DB cluster '{cluster_name}'")
        description = \
            self.rds_conn.get_db_cluster_description(cluster_name)

        if not description:
            _LOG.warning(f'RDS DB cluster {cluster_name} is not found')
            return {arn: config}

        if description.get('DeletionProtection') is True:
            if not click_confirm(
                    f"The '{cluster_name}' has deletion protection "
                    f"enabled. Do you want to proceed with deletion?"):
                USER_LOG.info(
                    f"RDS DB cluster '{cluster_name}' deletion skipped")
                return {}

            self._disable_db_cluster_del_protection(cluster_name)

        self.rds_conn.delete_db_cluster(cluster_name)

        USER_LOG.info(f"Waiting for DB cluster '{cluster_name}' deletion...")
        waiter = self.rds_conn.get_waiter('db_cluster_deleted')
        waiter.wait(DBClusterIdentifier=cluster_name)
        _LOG.info(f"RDS DB cluster '{cluster_name}' was removed.")

        return {arn: config}

    def _disable_db_cluster_del_protection(self, name: str):
        USER_LOG.info(
            'Disabling DB cluster deletion protection. Please wait.'
        )
        self.rds_conn.update_db_cluster({
            'DBClusterIdentifier': name,
            'DeletionProtection': False
        })

        USER_LOG.info(
            f"Waiting for the DB cluster '{name}' to become available...")
        waiter = self.rds_conn.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )


class RDSDBInstanceResource(BaseResource):

    def __init__(self, rds_conn: RDSConnection) -> None:
        self.rds_conn = rds_conn

    def create_db_instance(self, args: list) -> dict | tuple:
        """ Create RDS db instance in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_db_instance_from_meta, args, 1)

    @unpack_kwargs
    def _create_db_instance_from_meta(self, name: str, meta: dict) -> dict:
        """ Create RDS db instance from meta description.

        :type name: str
        :type meta: dict
        """
        validate_params(name, meta, DB_INSTANCE_REQUIRED_PARAMS)

        cluster_name = meta.pop('cluster_name', None)

        description = self.rds_conn.get_db_instance_description(
            cluster_name=cluster_name,
            instance_name=name
        )
        if description:
            _LOG.warning(f'RDS DB instance {name} already exists.')
            return self.describe_db_instance(
                name=name, meta=meta, description=description)

        params = copy.deepcopy(meta)
        params.pop('resource_type')

        validate_known_params(name, list(params.keys()),
                              DEPLOY_DB_INSTANCE_KNOWN_PARAMS)

        instance_class = params.pop('instance_class', None)
        database_name = params.pop('database_name', None)
        iam_db_auth = params.pop('iam_db_auth', None)
        db_subnet_group_name = params.pop('db_subnet_group_name', None)

        params = dict_keys_to_upper_camel_case(params)

        if cluster_name is not None:
            params['DBClusterIdentifier'] = cluster_name

        if instance_class is not None:
            params['DBInstanceClass'] = instance_class

        if database_name is not None:
            params['DBName'] = database_name

        if iam_db_auth is not None:
            params['EnableIAMDatabaseAuthentication'] = iam_db_auth

        if db_subnet_group_name is not None:
            params['DBSubnetGroupName'] = db_subnet_group_name

        description = self.rds_conn.create_db_instance(
            name=name,
            params=params
        )

        USER_LOG.info(
            f"Waiting for the DB instance '{name}' to become available. This "
            f"may take up to 15 minutes. Please refrain from interrupting."
        )
        waiter = self.rds_conn.get_waiter('db_instance_available')
        waiter.wait(
            DBInstanceIdentifier=name
        )

        return self.describe_db_instance(
            name=name,
            meta=meta,
            description=description
        )

    def update_db_instance(self, args: list) -> dict | tuple:
        return self.create_pool(self._update_db_instance, args, 1)

    @unpack_kwargs
    def _update_db_instance(self, name: str, meta: dict, context) -> dict:
        instance = self.rds_conn.get_db_instance_description(
            cluster_name=meta.get('cluster_name'),
            instance_name=name
        )
        if not instance:
            raise ResourceNotFoundError(
                f"RDS DB instance '{name}' does not exist."
            )

        params = copy.deepcopy(meta)

        # TODO implement tags updating
        params.pop('tags', None)

        for key in UPDATE_INSTANCE_NOT_SUPPORTED_KEYS:
            params.pop(key, None)

        validate_known_params(
            name,
            list(params.keys()),
            UPDATE_DB_INSTANCE_KNOWN_PARAMS
        )

        instance_class = params.pop('instance_class', None)
        database_name = params.pop('database_name', None)
        iam_db_auth = params.pop('iam_db_auth', None)
        db_subnet_group_name = params.pop('db_subnet_group_name', None)

        params = dict_keys_to_upper_camel_case(params)

        params['DBInstanceIdentifier'] = name

        if instance_class is not None:
            params['DBInstanceClass'] = instance_class

        if database_name is not None:
            params['DBName'] = database_name

        if iam_db_auth is not None:
            params['EnableIAMDatabaseAuthentication'] = iam_db_auth

        if db_subnet_group_name is not None:
            params['DBSubnetGroupName'] = db_subnet_group_name

        _LOG.info('Updating db instance...')
        description = self.rds_conn.update_db_instance(
            params=params
        )

        USER_LOG.info(
            f"Waiting for DB instance '{name}' to become available...")
        waiter = self.rds_conn.get_waiter('db_instance_available')
        waiter.wait(DBInstanceIdentifier=name)

        _LOG.info(f"RDS DB instance '{name}' updated successfully")

        return self.describe_db_instance(
            name=name,
            meta=meta,
            description=description
        )

    def describe_db_instance(self, name: str, meta: dict,
                             description: dict = None) -> dict:
        if not description:
            description = self.rds_conn.get_db_instance_description(
                cluster_name=meta.get('cluster_name'),
                instance_name=name
            )
            if not description:
                return {}

        arn = description['DBInstanceArn']

        return {
            arn: build_description_obj(description, name, meta)
        }

    def remove_db_instance(self, args: list) -> dict | tuple:
        return self.create_pool(self._remove_db_instance, args)

    @unpack_kwargs
    def _remove_db_instance(self, arn: str, config: dict) -> dict:
        from click import confirm as click_confirm

        instance_name = config['resource_name']
        db_cluster_name = \
            config['resource_meta'].get('cluster_name', '')

        instance_description = \
            self.rds_conn.get_db_instance_description(
                cluster_name=db_cluster_name,
                instance_name=instance_name)

        if not instance_description:
            _LOG.warning(f'RDS DB instance {instance_name} is not found')
            return {arn: config}

        USER_LOG.info(f"Deleting RDS DB instance '{instance_name}'")

        cluster_del_protection = \
            self.rds_conn.is_db_cluster_del_protection(db_cluster_name)
        if cluster_del_protection:
            if not click_confirm(
                    f"The '{instance_name}' DB cluster has deletion "
                    f"protection enabled. Do you want to proceed with "
                    f"deletion?"):
                return {}

            self.rds_conn.disable_db_cluster_del_protection(db_cluster_name)

        if instance_description.get('DeletionProtection') is True:
            if not click_confirm(
                    f"The '{instance_name}' has deletion protection "
                    f"enabled. Do you want to proceed with deletion?"):
                return {}

            self.rds_conn.disable_db_instance_del_protection(instance_name)

        self.rds_conn.delete_db_instance(instance_name)

        USER_LOG.info(
            f"Waiting for DB instance '{instance_name}' deletion. This may "
            f"take up to 15 minutes. Please refrain from interrupting.")
        waiter = self.rds_conn.get_waiter('db_instance_deleted')
        waiter.wait(DBInstanceIdentifier=instance_name)
        _LOG.info(f"RDS DB instance '{instance_name}' was removed.")

        if cluster_del_protection:
            self.rds_conn.enable_db_cluster_del_protection(db_cluster_name)

        return {arn: config}
