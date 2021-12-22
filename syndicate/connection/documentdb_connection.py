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

_LOG = get_logger('syndicate.connection.documentdb_connection')


@apply_methods_decorator(retry)
class DocumentDBConnection(object):
    """ DynamoDB class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('docdb', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new DocumentDB connection.')

    def create_db_cluster(self, identifier, vpc_security_group_ids=None,
                          port=None, availability_zones=None,
                          master_username=None, master_password=None):
        """
        Creates a new Amazon DocumentDB cluster.
        """
        params = {
            'DBClusterIdentifier': identifier,
            'Engine': 'docdb'
        }
        if vpc_security_group_ids:
            params['VpcSecurityGroupIds'] = list(vpc_security_group_ids)
        if port:
            params['Port'] = port
        if availability_zones:
            params['AvailabilityZones'] = list(availability_zones)
        if master_username:
            params['MasterUsername'] = master_username
        if master_password:
            params['MasterUserPassword'] = master_password

        response = self.client.create_db_cluster(**params)
        return response['DBCluster'].get('DBClusterIdentifier')

    def create_db_instance(self, instance_identifier, cluster_identifier,
                           instance_class, availability_zone=None):
        """
        Creates a new instance.
        """
        params = {
            'DBInstanceIdentifier': instance_identifier,
            'DBInstanceClass': instance_class,
            'DBClusterIdentifier': cluster_identifier,
            'Engine': 'docdb'
        }
        if availability_zone:
            params['AvailabilityZone'] = availability_zone

        response = self.client.create_db_instance(**params)
        return response['DBInstance'].get('DBInstanceIdentifier')

    def delete_db_instance(self, instance_identifier):
        """
        Deletes a previously provisioned instance.
        """
        response = self.client.delete_db_instance(
            DBInstanceIdentifier=instance_identifier)
        return response['DBInstance'].get('DBInstanceIdentifier')

    def delete_db_cluster(self, cluster_identifier, skip_final_snapshot=True,
                          final_db_snapshot_identifier=None):
        """
        Deletes a previously provisioned cluster (all automated backups for
        that cluster are deleted and can't be recovered).
        """
        if skip_final_snapshot and final_db_snapshot_identifier:
            raise AssertionError(
                'Only one of this parameters must set to \'true\': '
                'skip_final_snapshot, final_db_snapshot_identifier')

        if not skip_final_snapshot and not final_db_snapshot_identifier:
            raise AssertionError(
                'One of this parameters must set to \'true\': '
                'skip_final_snapshot, final_db_snapshot_identifier')

        params = {
            'DBClusterIdentifier': cluster_identifier,
            'SkipFinalSnapshot': skip_final_snapshot,
        }
        if final_db_snapshot_identifier:
            params['FinalDBSnapshotIdentifier'] = final_db_snapshot_identifier
        response = self.client.delete_db_cluster(**params)
        return response['DBCluster'].get('DBClusterIdentifier')

    def describe_db_clusters(self, identifier):
        """
        Describes provisioned Amazon DocumentDB clusters.
        """
        params = {
            'DBClusterIdentifier': identifier
        }
        try:
            response = self.client.describe_db_clusters(**params)
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBClusterNotFoundFault':
                _LOG.warn(f'DocumentDB cluster \'{identifier}\' is not found')
                return None
            else:
                raise e
        return response['DBClusters'][0].get('DBClusterIdentifier')

    def describe_db_instances(self, instance_identifier):
        """
        Describes provisioned Amazon DocumentDB instances.
        """
        params = {
            'DBInstanceIdentifier': instance_identifier
        }
        try:
            response = self.client.describe_db_instances(**params)
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceNotFound':
                _LOG.warn(f'DocumentDB instance \'{instance_identifier}\' is '
                          f'not found')
                return None
            else:
                raise e
        return response['DBInstances'][0].get('DBInstanceIdentifier')

