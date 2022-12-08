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
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import (
    unpack_kwargs)
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.documentdb_resource')


class DocumentDBClusterResource(BaseResource):

    def __init__(self, docdb_conn, account_id,
                 region) -> None:
        self.connection = docdb_conn
        self.account_id = account_id
        self.region = region

    def create_db_cluster(self, args):
        """ Create DocumentDB cluster in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_db_cluster_from_meta,
                                args)

    def describe_documentdb_cluster(self, identifier, meta):
        if not identifier:
            return
        response = self.connection.describe_db_clusters(identifier)
        if not response:
            return
        arn = f'arn:aws:rds:{self.region}:{self.account_id}:' \
              f'cluster:{identifier}'
        return {
            arn: build_description_obj(response, identifier, meta)
        }

    @unpack_kwargs
    def _create_db_cluster_from_meta(self, name, meta):
        pool_id = self.connection.describe_db_clusters(name)
        if pool_id:
            _LOG.warn(f'\'{name}\' cluster exists.')
            return self.describe_documentdb_cluster(identifier=name, meta=meta)

        _LOG.info(f'Creating documentDB cluster {name}')
        vpc_security_group_ids = meta.get('vpc_security_group_ids', None)
        if vpc_security_group_ids and not isinstance(
                vpc_security_group_ids, list):
            _LOG.warn(f'Incorrect type for vpc_security_group_ids: '
                      f'{vpc_security_group_ids}')
            vpc_security_group_ids = None

        availability_zones = meta.get('availability_zones', None)
        if availability_zones and not isinstance(
                availability_zones, list):
            _LOG.warn(f'Incorrect type for availability_zones: '
                      f'{availability_zones}')
            availability_zones = None
        port = meta.get('port', None)
        master_username = meta.get('master_username', None)
        if master_username and master_username[0].isdigit():
            raise AssertionError(f'The first character of master username '
                                 f'must be a letter: {master_username}')
        master_password = meta.get('master_password', None)
        if master_password and any(
                char in master_password for char in ('"', '@', '/')):
            raise AssertionError(
                f'The password cannot contain forward slash (/), double quote '
                f'(") or the "at" symbol (@): {master_password}')
        cluster = self.connection.create_db_cluster(
            identifier=name, availability_zones=availability_zones,
            vpc_security_group_ids=vpc_security_group_ids, port=port,
            master_password=master_password, master_username=master_username)
        _LOG.info(f'Created documentDB cluster {cluster}')
        return self.describe_documentdb_cluster(identifier=name, meta=meta)

    def remove_db_cluster(self, args):
        self.create_pool(self._remove_db_cluster, args)

    @unpack_kwargs
    def _remove_db_cluster(self, arn, config):
        cluster = config['description']
        try:
            self.connection.delete_db_cluster(cluster)
            _LOG.info(f'DocumentDB cluster \'{cluster}\' was removed')
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn(f'DocumentDB cluster \'{cluster}\' is not found')
            else:
                raise e
