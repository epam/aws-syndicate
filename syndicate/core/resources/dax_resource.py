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
from time import time

from syndicate.commons import deep_get
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.helper import retry
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')
USER_LOG = get_user_logger()


class DaxResource(BaseResource):
    def __init__(self, dax_conn, iam_conn):
        self.dax_conn = dax_conn
        self.iam_conn = iam_conn

    def create_cluster(self, args):
        return self.create_pool(self._create_cluster_from_meta, args)

    @unpack_kwargs
    def _create_cluster_from_meta(self, name, meta):
        role_name = meta['iam_role_name']
        role_arn = self.iam_conn.check_if_role_exists(role_name)
        if not role_arn:
            message = f'Role {role_name} does not exist; ' \
                      f'Dax cluster {name} failed to be created.'
            _LOG.error(message)
            raise AssertionError(message)
        subnet_group_name = meta.get('subnet_group_name')
        subnet_ids = meta.get('subnet_ids') or []
        if subnet_ids:
            _LOG.info(f'Subnet_ids \'{subnet_ids}\' were given. '
                      f'Creating Dax subnet group \'{subnet_group_name}\'')
            self.dax_conn.create_subnet_group(
                subnet_group_name=subnet_group_name,
                subnet_ids=subnet_ids
            )
            _LOG.info(f'Dax subnet group with name {subnet_group_name} '
                      f'was created.')
        elif subnet_group_name:
            _LOG.info(f'Subnet_ids were not given. Assuming that subnet '
                      f'group \'{subnet_group_name}\' already exists')
        response = self.dax_conn.create_cluster(
            cluster_name=name,
            node_type=meta['node_type'],
            replication_factor=meta['replication_factor'],
            iam_role_arn=role_arn,
            subnet_group_name=subnet_group_name,
            cluster_endpoint_encryption_type=meta.get('cluster_endpoint_encryption_type'),
            security_group_ids=meta.get('security_group_ids') or [],
            parameter_group_name=meta.get('parameter_group_name'),
            availability_zones=meta.get('availability_zones') or []
        )
        if response:
            _LOG.info(f'Dax cluster \'{name}\' was successfully created')
            return self.describe_cluster(name, meta, response['Cluster'])
        else:
            _LOG.warning(f'Dax cluster \'{name}\' was not created because '
                         f'it already exists')
            return self.describe_cluster(name, meta)

    def describe_cluster(self, name, meta, response=None):
        if not response:
            response = self.dax_conn.describe_cluster(name)
        if response:
            arn = response['ClusterArn']
            del response['ClusterArn']
            return {
                arn: build_description_obj(response, name, meta)
            }

    def remove_cluster(self, args):
        return self.create_pool(self._remove_cluster, args)

    @unpack_kwargs
    def _remove_cluster(self, arn, config):
        cluster_name = config['resource_name']
        subnet_group_name = deep_get(config,
                                     ['resource_meta', 'subnet_group_name']) \
            if deep_get(config, ['resource_meta', 'subnet_ids']) else None
        try:
            self.dax_conn.delete_cluster(cluster_name)
        except self.dax_conn.client.exceptions.InvalidClusterStateFault as e:
            USER_LOG.warning(e.response['Error']['Message'] +
                             ' Remove it manually!')
        if subnet_group_name:
            self._remove_subnet_group(subnet_group_name)

    def _remove_subnet_group(self, subnet_group_name):
        USER_LOG.info(f"Deleting subnet group '{subnet_group_name}'. "
                      f"Please wait it may take up to 10 minutes.")
        self.dax_conn.delete_subnet_group(subnet_group_name)
        _LOG.info(f"Subnet group '{subnet_group_name}' removed successfully.")
