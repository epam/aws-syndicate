"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.helper import prettify_json

_LOG = get_logger(__name__)


@apply_methods_decorator(retry())
class RDSConnection(object):
    """ AWS RDS connection class. """

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('rds', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        self.region = region
        _LOG.debug('Opened new RDS connection.')

    def create_db_cluster(self, name: str, params: dict) -> dict:
        params = dict(
            DBClusterIdentifier=name,
            **params
        )
        _LOG.debug(f'DB cluster creation params: {prettify_json(params)}')

        return self.client.create_db_cluster(**params)['DBCluster']

    def create_db_instance(self, name: str, params: dict) -> dict:
        params = dict(
            DBInstanceIdentifier=name,
            **params
        )
        _LOG.debug(f'DB instance creation params: {prettify_json(params)}')

        return self.client.create_db_instance(**params)['DBInstance']

    def get_db_cluster_description(self, name: str) -> dict | None:
        try:
            response = self.client.describe_db_clusters(
                DBClusterIdentifier=name)
            return response['DBClusters'][0] if response['DBClusters'] \
                else {}
        except ClientError as e:

            if e.response['Error']['Code'] == 'DBClusterNotFoundFault':
                _LOG.info(f'RDS DB cluster {name} is not found')
                return {}

            else:
                raise e

    def get_db_instance_description(self, cluster_name: str = None,
                                    instance_name: str = None) -> dict:
        params = dict()

        if cluster_name:
            params['Filters'] = [
                {
                    'Name': 'db-cluster-id',
                    'Values': [cluster_name]
                }
            ]

        if instance_name:
            params['DBInstanceIdentifier'] = instance_name

        try:
            response = self.client.describe_db_instances(**params)
            return response['DBInstances'][0] if response['DBInstances'] \
                else {}
        except ClientError as e:

            if e.response['Error']['Code'] == 'DBInstanceNotFound':
                _LOG.info(f'RDS DB instance is not found')
                return {}

            else:
                raise e

    def get_db_cluster_endpoint(self, cluster_name: str) -> str:
        descr = self.get_db_cluster_description(cluster_name)
        return descr.get('Endpoint')

    def get_db_cluster_reader_endpoint(self, cluster_name: str) -> str:
        descr = self.get_db_cluster_description(cluster_name)
        return descr.get('ReaderEndpoint')

    def extract_secret_name_from_arn(self, arn: str) -> str:
        arn_tail = arn.split(':')[-1]
        name_parts = arn_tail.split('-')
        name_parts.pop(-1)
        return '-'.join(name_parts)

    def get_db_cluster_master_user_secret_name(self, cluster_name: str) -> str:
        descr = self.get_db_cluster_description(cluster_name)
        secret = descr.get('MasterUserSecret', {})
        if secret_arn := secret.get('SecretArn'):
            return self.extract_secret_name_from_arn(secret_arn)

    def get_waiter(self, waiter_name: str):
        return self.client.get_waiter(waiter_name)

    def update_db_instance(self, params: dict) -> dict:
        return self.client.modify_db_instance(**params)['DBInstance']

    def update_db_cluster(self, params: dict) -> dict:
        return self.client.modify_db_cluster(**params)['DBCluster']

    def delete_db_instance(self, instance_name: str):
        return self.client.delete_db_instance(
            DBInstanceIdentifier=instance_name,
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True
        )

    def delete_db_cluster(self, name: str):
        return self.client.delete_db_cluster(
            DBClusterIdentifier=name,
            SkipFinalSnapshot=True
        )

    def is_db_cluster_del_protection(self, name: str) -> bool:
        description = self.get_db_cluster_description(name)
        return description.get('DeletionProtection')

    def is_db_instance_del_protection(self, name: str) -> bool:
        description = self.get_db_instance_description(name)
        return description.get('DeletionProtection')

    def disable_db_cluster_del_protection(self, name: str):
        _LOG.info(
            'Disabling DB cluster deletion protection...'
        )
        self.update_db_cluster({
            'DBClusterIdentifier': name,
            'DeletionProtection': False
        })

        _LOG.info(
            'Waiting for the DB cluster to become available...')
        waiter = self.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )

    def enable_db_cluster_del_protection(self, name: str):
        _LOG.info(
            'Enabling DB cluster deletion protection...'
        )
        self.update_db_cluster({
            'DBClusterIdentifier': name,
            'DeletionProtection': True
        })

        _LOG.info(
            'Waiting for the DB cluster to become available...')
        waiter = self.get_waiter('db_cluster_available')
        waiter.wait(
            DBClusterIdentifier=name
        )

    def disable_db_instance_del_protection(self, name: str):
        _LOG.info(
            'Disabling DB instance deletion protection...'
        )
        self.update_db_instance({
            'DBInstanceIdentifier': name,
            'DeletionProtection': False
        })

        _LOG.info(
            'Waiting for the DB instance to become available...')
        waiter = self.get_waiter('db_instance_available')
        waiter.wait(
            DBInstanceIdentifier=name
        )
