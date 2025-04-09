import copy

from botocore.exceptions import ClientError

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
    'd_b_instance_identifier',
    'd_b_instance_class',
    'engine'
]

DEPLOY_CLUSTER_KNOWN_PARAMS = [
    'db_instance_config',
    'availability_zones',
    'backup_retention_period',
    'character_set_name',
    'database_name',
    'd_b_cluster_parameter_group_name',
    'vpc_security_group_ids',
    'd_b_subnet_group_name',
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
    'enable_i_a_m_database_authentication',
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
    'db_instance_config',
    'apply_immediately',
    'backup_retention_period',
    'd_b_cluster_parameter_group_name',
    'vpc_security_group_ids',
    'port',
    'master_user_password',
    'option_group_name',
    'preferred_backup_window',
    'preferred_maintenance_window',
    'enable_i_a_m_database_authentication',
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
    'd_b_name',
    'd_b_instance_identifier',
    'allocated_storage',
    'd_b_instance_class',
    'engine',
    'master_username',
    'master_user_password',
    'd_b_security_groups',
    'vpc_security_group_ids',
    'availability_zone',
    'd_b_subnet_group_name',
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
    'd_b_cluster_identifier',
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
    'enable_i_a_m_database_authentication',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'enable_cloudwatch_logs_exports',
    'processor_features',
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
    'd_b_instance_identifier',
    'allocated_storage',
    'd_b_instance_class',
    'd_b_subnet_group_name',
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
    'new_d_b_instance_identifier',
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
    'enable_i_a_m_database_authentication',
    'enable_performance_insights',
    'performance_insights_k_m_s_key_id',
    'performance_insights_retention_period',
    'cloudwatch_logs_export_configuration',
    'processor_features',
    'use_default_processor_features',
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
    'availability_zones'
]


class RDSAuroraResource(BaseResource):

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

        tags = params.get('tags', [])
        db_instance_config = params.pop('db_instance_config', {})

        validate_params('db_instance', db_instance_config,
                        DB_INSTANCE_REQUIRED_PARAMS)

        validate_known_params(
            db_instance_config['d_b_instance_identifier'],
            list(db_instance_config.keys()),
            DEPLOY_DB_INSTANCE_KNOWN_PARAMS
        )

        cluster_description = self.rds_conn.create_db_cluster(
            name=name,
            params=dict_keys_to_upper_camel_case(params)
        )

        USER_LOG.info(
            'Waiting for the DB cluster to become available...')
        waiter = self.rds_conn.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )

        USER_LOG.info(f'Endpoint: {cluster_description["Endpoint"]}')
        USER_LOG.info(
            f'Reader endpoint: {cluster_description["ReaderEndpoint"]}')
        if cluster_description.get('CustomEndpoints'):
            endpoints = '\n'.join(cluster_description['CustomEndpoints'])
            USER_LOG.info(f'Custom endpoints: {endpoints}')

        if db_instance_config:
            db_instance_config['tags'] = tags
            db_instance_params = \
                dict_keys_to_upper_camel_case(db_instance_config)

            instance_description = self.rds_conn.create_db_instance(
                cluster_name=name,
                params=db_instance_params
            )

            USER_LOG.info(
                'Waiting for the DB instance to become available. This may '
                'take up to 15 minutes. Please refrain from interrupting.'
            )
            waiter = self.rds_conn.get_waiter('db_instance_available')
            waiter.wait(
                DBInstanceIdentifier=db_instance_params['DBInstanceIdentifier']
            )

            cluster_description['db_instance_description'] = \
                instance_description

        return self.describe_db_cluster(
            name=name,
            meta=meta,
            description=cluster_description
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

        params['d_b_cluster_identifier'] = name
        db_instance_config = params.pop('db_instance_config', {})

        cluster_description = self.rds_conn.update_db_cluster(
            params=dict_keys_to_upper_camel_case(params)
        )

        USER_LOG.info(f'Endpoint: {cluster_description["Endpoint"]}')
        USER_LOG.info(
            f'Reader endpoint: {cluster_description["ReaderEndpoint"]}')
        if cluster_description.get('CustomEndpoints'):
            endpoints = '\n'.join(cluster_description['CustomEndpoints'])
            USER_LOG.info(f'Custom endpoints: {endpoints}')

        if db_instance_config:
            validate_params('db_instance', db_instance_config,
                            DB_INSTANCE_REQUIRED_PARAMS)

            # TODO implement tags updating
            db_instance_config.pop('tags', None)
            db_instance_config.pop('engine', None)

            validate_known_params(
                db_instance_config['d_b_instance_identifier'],
                list(db_instance_config.keys()),
                UPDATE_DB_INSTANCE_KNOWN_PARAMS
            )

            db_instance_params = dict_keys_to_upper_camel_case(
                db_instance_config)
            
            db_instance_descr = self.rds_conn.describe_db_instances(
                    cluster_name=name,
                    instance_name=db_instance_params['DBInstanceIdentifier']
                )

            if db_instance_descr:
                _LOG.info('Updating db instance...')
                instance_description = self.rds_conn.update_db_instance(
                    params=db_instance_params
                )

                USER_LOG.info('Waiting for DB cluster to become available...')
                waiter = self.rds_conn.get_waiter('db_instance_available')
                waiter.wait(
                    DBInstanceIdentifier=db_instance_params[
                        'DBInstanceIdentifier']
                )
            else:
                _LOG.warning(
                    f"DB instance "
                    f"'{db_instance_params['DBInstanceIdentifier']}' not "
                    f"found."
                )
                instance_description = {}

            cluster_description['db_instance_description'] = \
                instance_description

        _LOG.info(f"RDS DB cluster '{name}' updated successfully")

        return self.describe_db_cluster(
            name=name,
            meta=meta,
            description=cluster_description
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
        cluster_name = config['resource_name']
        db_instances = self.rds_conn.describe_db_instances(cluster_name)

        for instance in db_instances:
            instance_name = instance['DBInstanceIdentifier']
            USER_LOG.info(f"Deleting DB instance '{instance_name}'")
            self.rds_conn.delete_db_instance(instance_name)

            USER_LOG.info(
                'Waiting for DB instance deletion. This may take up to 15 '
                'minutes. Please refrain from interrupting.'
            )
            waiter = self.rds_conn.get_waiter('db_instance_deleted')
            waiter.wait(DBInstanceIdentifier=instance_name)
        try:
            USER_LOG.info(f"Deleting RDS DB cluster '{cluster_name}'")
            cluster_description = \
                self.rds_conn.get_db_cluster_description(cluster_name)

            if cluster_description.get('DeletionProtection') is True:
                self._disable_db_cluster_del_protection(cluster_name)

            self.rds_conn.delete_db_cluster(cluster_name)

            USER_LOG.info('Waiting for DB cluster deletion...')
            waiter = self.rds_conn.get_waiter('db_cluster_deleted')
            waiter.wait(DBClusterIdentifier=cluster_name)
            _LOG.info(f"RDS DB cluster '{cluster_name}' was removed.")

            return {arn: config}

        except ClientError as e:

            if e.response['Error']['Code'] == 'DBClusterNotFoundFault':
                _LOG.warning(f'RDS DB cluster {cluster_name} is not found')
                return {arn: config}

            else:
                raise e

    def _disable_db_cluster_del_protection(self, name: str):
        USER_LOG.info(
            'Disabling DB cluster deletion protection. Please wait.'
        )
        self.rds_conn.update_db_cluster({
            'DBClusterIdentifier': name,
            'DeletionProtection': False
        })

        USER_LOG.info(
            'Waiting for the DB cluster to become available...')
        waiter = self.rds_conn.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )
