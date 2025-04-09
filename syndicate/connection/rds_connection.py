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

# ------------------------ Create ------------------------

    def create_db_cluster(self, name: str, params: dict) -> dict:
        params = dict(
            DBClusterIdentifier=name,
            **params
        )
        _LOG.debug(f'DB cluster creation params: {prettify_json(params)}')

        return self.client.create_db_cluster(**params)['DBCluster']

    def create_db_instance(self, cluster_name: str, params: dict) -> dict:
        params = dict(
            DBClusterIdentifier=cluster_name,
            **params
        )
        _LOG.debug(f'DB instance creation params: {prettify_json(params)}')

        return self.client.create_db_instance(**params)['DBInstance']

# ------------------------ Get ------------------------

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

    def get_waiter(self, waiter_name: str):
        return self.client.get_waiter(waiter_name)

    def describe_db_instances(self, cluster_name: str,
                              instance_name: str = None) -> list:
        try:
            params = dict(
                Filters=[
                    {
                        'Name': 'db-cluster-id',
                        'Values': [cluster_name]
                    }
                ]
            )
            if instance_name:
                params['DBInstanceIdentifier'] = instance_name

            return self.client.describe_db_instances(**params)['DBInstances']
        except ClientError as e:

            if e.response['Error']['Code'] == 'DBInstanceNotFoundFault':
                _LOG.info(f'RDS DB instance is not found')
                return []

            else:
                raise e

# ------------------------ Update ------------------------

    def update_db_instance(self, params: dict) -> dict:
        return self.client.modify_db_instance(**params)['DBInstance']

    def update_db_cluster(self, params: dict) -> dict:
        return self.client.modify_db_cluster(**params)['DBCluster']

# ------------------------ Delete ------------------------

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
