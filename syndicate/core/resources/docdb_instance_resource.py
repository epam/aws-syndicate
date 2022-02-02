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
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.documentdb_resource')


class DocumentDBInstanceResource(BaseResource):

    def __init__(self, docdb_conn, account_id,
                 region) -> None:
        self.connection = docdb_conn
        self.account_id = account_id
        self.region = region

    def create_db_instance(self, args):
        """ Create DocumentDB instance in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_db_instance_from_meta,
                                args)

    def describe_documentdb_instance(self, identifier, meta):
        if not identifier:
            return
        response = self.connection.describe_db_instances(identifier)
        if not response:
            return
        arn = f'arn:aws:rds:{self.region}:{self.account_id}:' \
              f'db:{identifier}'
        return {
            arn: build_description_obj(response, identifier, meta)
        }

    @unpack_kwargs
    def _create_db_instance_from_meta(self, name, meta):
        instance = self.connection.describe_db_instances(name)
        if instance:
            _LOG.warn(f'\'{name}\' instance exists.')
            return self.describe_documentdb_instance(identifier=name,
                                                     meta=meta)

        _LOG.info(f'Creating documentDB instance {name}')
        cluster_identifier = meta.get('cluster_identifier', None)
        instance_class = meta.get('instance_class', None)
        availability_zone = meta.get('availability_zone', None)
        instance = self.connection.create_db_instance(
            instance_identifier=name, availability_zone=availability_zone,
            instance_class=instance_class,
            cluster_identifier=cluster_identifier)

        _LOG.info(f'Created documentDB instance {instance}')
        return self.describe_documentdb_instance(identifier=name, meta=meta)

    def remove_db_instance(self, args):
        self.create_pool(self._remove_db_instance, args)

    @unpack_kwargs
    def _remove_db_instance(self, arn, config):
        instance = config['description']
        try:
            self.connection.delete_db_instance(instance)
            _LOG.info(f'DocumentDB instance \'{instance}\' was removed')
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn(f'DocumentDB instance \'{instance}\' is not found')
            else:
                raise e
