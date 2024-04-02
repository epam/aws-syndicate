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

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.dax_connection')


@apply_methods_decorator(retry())
class DaxConnection:
    """DynamoDB DAX connection clas"""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('dax', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new DAX connection.')

    def create_cluster(self, cluster_name: str, node_type: str,
                       replication_factor: str, iam_role_arn: str,
                       subnet_group_name: str = None,
                       cluster_endpoint_encryption_type: str = 'TLS',
                       security_group_ids: list = None,
                       parameter_group_name: str = None,
                       availability_zones: list = None):
        params = dict(
            ClusterName=cluster_name,
            NodeType=node_type,
            ReplicationFactor=replication_factor,
            IamRoleArn=iam_role_arn,
            SubnetGroupName=subnet_group_name,
            SecurityGroupIds=security_group_ids,
            ParameterGroupName=parameter_group_name,
            AvailabilityZones=availability_zones,
            ClusterEndpointEncryptionType=cluster_endpoint_encryption_type
        )
        params = {key: value for key, value in params.items() if value}
        try:
            return self.client.create_cluster(**params)
        except self.client.exceptions.ClusterAlreadyExistsFault as e:
            _LOG.warning(f'Cluster \'{cluster_name}\' already exists')
            return

    def describe_cluster(self, cluster_name):
        try:
            response = self.client.describe_clusters(
                ClusterNames=[cluster_name],
            )
            return response['Clusters'][0]
        except self.client.exceptions.ClusterNotFoundFault:
            _LOG.warning(f'Cluster \'{cluster_name}\' not found')
            return

    def delete_cluster(self, cluster_name):
        try:
            return self.client.delete_cluster(ClusterName=cluster_name)
        except self.client.exceptions.ClusterNotFoundFault:
            _LOG.warning(f'Dax cluster with name \'{cluster_name}\' not found')
            return

    def create_subnet_group(self, subnet_group_name, subnet_ids):
        params = dict(
            SubnetGroupName=subnet_group_name,
            SubnetIds=subnet_ids
        )
        return self.client.create_subnet_group(**params)

    def describe_subnet_group(self, subnet_group_name: str):
        try:
            return self.client.describe_subnet_groups(
                SubnetGroupNames=[subnet_group_name]
            )['SubnetGroups'][0]
        except self.client.exceptions.SubnetGroupNotFoundFault:
            _LOG.warning(f'Subnet group \'{subnet_group_name}\' not found')
            return

    @retry(retry_timeout=120, retry_timeout_step=10)
    def delete_subnet_group(self, subnet_group_name: str):
        try:
            self.client.delete_subnet_group(
                SubnetGroupName=subnet_group_name
            )
        except self.client.exceptions.SubnetGroupNotFoundFault:
            _LOG.warning(f'Subnet group with name '
                         f'\'{subnet_group_name}\' not found')
            return
