import copy
from time import sleep

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.rds_connection import RDSConnection
from syndicate.core.helper import unpack_kwargs, dict_keys_to_upper_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params, \
    build_description_obj
from syndicate.exceptions import ResourceNotFoundError

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

CLUSTER_REQUIRED_PARAMS = ['engine']
DB_INSTANCE_REQUIRED_PARAMS = ['d_b_instance_identifier',
                               'd_b_instance_class', 'engine']
UPDATE_CLUSTER_NOT_SUPPORTED_KEYS = ['resource_type', 'engine',
                                     'master_username', 'database_name']


class RDSResource(BaseResource):

    def __init__(self, rds_conn: RDSConnection) -> None:
        self.rds_conn = rds_conn

    def create_rds_cluster(self, args):
        """ Create RDS cluster in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_rds_cluster_from_meta, args, 1)

    @unpack_kwargs
    def _create_rds_cluster_from_meta(self, name, meta):
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
        tags = params.pop('tags', [])
        params.pop('resource_type')
        db_instance_config = params.pop('db_instance_config', {})

        cluster_description = self.rds_conn.create_db_cluster(
            name=name,
            tags=tags,
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
            db_instance_config.pop('tags', None)
            db_instance_params = dict_keys_to_upper_camel_case(db_instance_config)

            instance_description = self.rds_conn.create_db_instance(
                cluster_name=name,
                tags=tags,
                params=db_instance_params
            )

            USER_LOG.warning(
                'Waiting for the DB instance to become available. This may '
                'take up to 15 minutes. Please refrain from interrupting '
                'the deployment.'
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

    def describe_db_cluster(self, name, meta, description=None):
        if not description:
            description = self.rds_conn.get_db_cluster_description(name)
            if not description:
                return {}

        arn = description['DBClusterArn']

        return {
            arn: build_description_obj(description, name, meta)
        }

    def remove_db_cluster(self, args):
        return self.create_pool(self._remove_db_cluster, args)

    @unpack_kwargs
    def _remove_db_cluster(self, arn, config):
        cluster_name = config['resource_name']
        db_instances = self.rds_conn.describe_db_instances(cluster_name)

        for instance in db_instances:
            instance_name = instance['DBInstanceIdentifier']
            USER_LOG.info(f"Deleting DB instance '{instance_name}'")

            if instance['DeletionProtection'] is True:
                self.rds_conn.update_db_instance({
                    'DBInstanceIdentifier': instance_name,
                    'DeletionProtection': False
                })
                USER_LOG.info(
                    'Disabling DB instance deletion protection. Please wait.'
                )
                waiter = self.rds_conn.get_waiter('db_instance_available')
                waiter.wait(DBInstanceIdentifier=instance_name)
            self.rds_conn.delete_db_instance(instance_name)
            USER_LOG.info(f"Waiting DB instance deletion...")
            waiter = self.rds_conn.get_waiter('db_instance_deleted')
            waiter.wait(DBInstanceIdentifier=instance_name)
        try:
            USER_LOG.info(f"Deleting RDS DB cluster '{cluster_name}'")
            self.rds_conn.delete_db_cluster(cluster_name)

            USER_LOG.info(f"Waiting DB cluster deletion...")
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

    def update_db_cluster(self, args):
        return self.create_pool(self._update_db_cluster, args, 1)

    @unpack_kwargs
    def _update_db_cluster(self, name, meta, context):
        cluster = self.rds_conn.get_db_cluster_description(name)
        if not cluster:
            raise ResourceNotFoundError(
                f"RDS DB cluster '{name}' does not exist."
            )

        params = copy.deepcopy(meta)
        params['d_b_cluster_identifier'] = name
        tags = params.pop('tags', [])

        for key in UPDATE_CLUSTER_NOT_SUPPORTED_KEYS:
            params.pop(key, None)

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

            db_instance_config.pop('tags', None)
            db_instance_params = dict_keys_to_upper_camel_case(
                db_instance_config)

            if self.rds_conn.describe_db_instances(
                    cluster_name=name,
                    instance_name=db_instance_params['DBInstanceIdentifier']
                ):
                _LOG.info('Updating db instance...')
                db_instance_params.pop('Engine')
                instance_description = self.rds_conn.update_db_instance(
                    params=db_instance_params
                )
                # because there is no waiter for updating
                sleep(60)
            else:
                _LOG.info('Creating db instance...')
                instance_description = self.rds_conn.create_db_instance(
                    cluster_name=name,
                    tags=tags,
                    params=db_instance_params
                )

                USER_LOG.warning(
                    'Waiting for the DB instance to become available. This '
                    'may take up to 15 minutes. Please refrain from '
                    'interrupting.'
                )
                waiter = self.rds_conn.get_waiter('db_instance_available')
                waiter.wait(
                    DBInstanceIdentifier=db_instance_params[
                        'DBInstanceIdentifier']
                )

            cluster_description['db_instance_description'] = \
                instance_description

        _LOG.info(f"RDS DB cluster '{name}' updated successfully")

        return self.describe_db_cluster(
            name=name,
            meta=meta,
            description=cluster_description
        )
