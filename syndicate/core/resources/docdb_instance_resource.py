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
    unpack_kwargs, dict_keys_to_capitalized_camel_case)
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
        response = self.connection.describe_db_instance(identifier)
        arn = f'arn:aws:rds:{self.region}:{self.account_id}:' \
              f'db/{identifier}'
        return {
            arn: build_description_obj(response, identifier, meta)
        }

    @unpack_kwargs
    def _create_db_instance_from_meta(self, name, meta):
        pool_id = self.connection.describe_db_instances(name)
        if pool_id:
            _LOG.warn(f'\'{name}\' instance exists.')
            return self.describe_documentdb_instance(identifier=name, meta=meta)

        _LOG.info(f'Creating documentDB instance {name}')
        cluster_identifier = meta.get('cluster_identifier', None)
        instance_class = meta.get('instance_class', None)
        availability_zones = meta.get('availability_zones', None)
        if availability_zones and not isinstance(
                availability_zones, list):
            _LOG.warn(f'Incorrect type for availability_zones: '
                      f'{availability_zones}')
            availability_zones = None
        instance = self.connection.create_db_instance(
            instance_identifier=name, availability_zones=availability_zones,
            instance_class=instance_class,
            cluster_identifier=cluster_identifier)

        _LOG.info(f'Created documentDB instance {instance}')
        return self.describe_documentdb_instance(identifier=name, meta=meta)

    def remove_cognito_user_pools(self, args):
        self.create_pool(self._remove_cognito_user_pools, args)

    @unpack_kwargs
    def _remove_cognito_user_pools(self, arn, config):
        pool_id = config['description']['UserPool']['Id']
        try:
            self.connection.remove_user_pool(pool_id)
            _LOG.info('Cognito user pool %s was removed', pool_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Cognito user pool %s is not found', id)
            else:
                raise e

    def get_user_pool_id(self, name):
        """
        Returns user pools ID by its name

        :param name: user pools name
        :return: user pools ID
        """
        return self.connection.if_pool_exists_by_name(user_pool_name=name)

    def cognito_resource_identifier(self, name, output=None):
        if output:
            # cognito currently is not located in different regions
            # process only first object
            pool_output = list(output.items())[0][1]
            # find id from the output
            return pool_output['description']['UserPool']['Id']
        return self.connection.if_pool_exists_by_name(name)

    def add_custom_attributes(self, user_pool_id, attributes):
        custom_attributes = []
        for attr in attributes:
            attr['attribute_data_type'] = attr.pop('type')
            custom_attributes.append(dict_keys_to_capitalized_camel_case(attr))
        self.connection.add_custom_attributes(user_pool_id, custom_attributes)

    @staticmethod
    def __validate_policies(policies):
        if not policies.get('minimum_length'):
            policies['minimum_length'] = 6
        if not policies.get('require_uppercase'):
            policies['require_uppercase'] = True
        if not policies.get('require_symbols'):
            policies['require_symbols'] = True
        if not policies.get('require_lowercase'):
            policies['require_lowercase'] = True
        if not policies.get('require_numbers'):
            policies['require_numbers'] = True

        return {'PasswordPolicy': dict_keys_to_capitalized_camel_case(
            policies)}
