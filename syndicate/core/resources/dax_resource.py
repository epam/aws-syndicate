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
from syndicate.commons.log_helper import get_logger
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.helper import build_description_obj


_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')


class DaxResource(BaseResource):
    def __init__(self, dax_conn, iam_conn):
        self.dax_conn = dax_conn
        self.iam_conn = iam_conn

    def create_cluster(self, args):
        return self.create_pool(self.create_cluster_from_meta, args)

    @unpack_kwargs
    def create_cluster_from_meta(self, name, meta):
        role_name = meta['iam_role_name']
        role_arn = self.iam_conn.check_if_role_exists(role_name)
        if not role_arn:
            raise AssertionError(f'Role {role_name} does not exist; '
                                 f'Dax cluster {name} failed to be created.')
        # subnet_ids = meta.get('subnet_ids') or []
        # if subnet_ids:
        #     self.dax_conn.create_subnet_group(
        #         subnet_group_name=f'{name}-subnet-group-syndicate'
        #     )
        breakpoint()
        response = self.dax_conn.create_cluster(
            cluster_name=name,
            node_type=meta['node_type'],
            replication_factor=meta['replication_factor'],
            iam_role_arn=role_arn,
            subnet_group_name=meta.get('subnet_group_name'),
            security_group_ids=meta.get('security_group_ids') or []
        )
        return self.describe_cluster(name, meta, response['Cluster'])

    def describe_cluster(self, name, meta, response=None):
        if not response:
            response = self.dax_conn.describe_cluster(name)
        if response:
            arn = response['ClusterArn']
            del response['ClusterArn']
            return {
                arn: build_description_obj()
            }

    def remove_cluster(self):
        pass
