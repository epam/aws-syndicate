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
import re
import click
import sys

from syndicate.core.build.validator import assert_required_property

HASH_KEY_NAME = 'hash_key_name'
HASH_KEY_TYPE = 'hash_key_type'

SORT_KEY_NAME = 'sort_key_name'
SORT_KEY_TYPE = 'sort_key_type'

INDEX_KEY_TYPE = 'index_key_type'
INDEX_KEY_NAME = 'index_key_name'

INDEX_SORT_KEY_TYPE = 'index_sort_key_type'
INDEX_SORT_KEY_NAME = 'index_sort_key_name'

NAME = 'name'

LOCAL_INDEXES = 'local_indexes'

dynamodb_valid_key_types = ['S', 'N', 'B']


def validate_dynamodb(table_name, table_meta):
    """
    Performs check of DynamoDB resources.
    :param table_name: name of resource
    :param table_meta: resource definition
    :raises AssertionError in case of invalidity.
    :return: None
    """
    # check hash key
    _assert_key(meta=table_meta,
                res_name=table_name,
                key_name_attr=HASH_KEY_NAME,
                key_type_attr=HASH_KEY_TYPE)
    hash_key_type = table_meta[HASH_KEY_TYPE]
    if hash_key_type not in dynamodb_valid_key_types:
        raise AssertionError(
            'Hash key type of Table {0} is unsupported by DynamoDB. '
            'Valid types are {1}'.format(table_name, dynamodb_valid_key_types))

    # check sort key
    if table_meta.get(SORT_KEY_NAME):
        _assert_key(meta=table_meta,
                    res_name=table_name,
                    key_name_attr=SORT_KEY_NAME,
                    key_type_attr=SORT_KEY_TYPE)
        table_sort_key_type = table_meta[SORT_KEY_TYPE]
        if table_sort_key_type not in dynamodb_valid_key_types:
            raise AssertionError(
                'Sort key type of Table {0} is unsupported by DynamoDB. '
                'Valid types are {1}'.format(table_name,
                                             dynamodb_valid_key_types))

    # check LSIs
    if table_meta.get(LOCAL_INDEXES):
        for index in table_meta.get(LOCAL_INDEXES):
            index_name = index.get(NAME)
            assert_required_property(
                resource_name=index_name,
                property_name='local_indexes.{0}'.format(NAME),
                property_value=index_name)
            # both keys are required for LSI
            index_key_name = index.get(INDEX_KEY_NAME)
            assert_required_property(resource_name=INDEX_KEY_NAME,
                                     property_name='local_indexes.{0}'.format(
                                         INDEX_KEY_NAME),
                                     property_value=index_key_name)
            index_key_type_value = index.get(INDEX_KEY_TYPE)
            assert_required_property(resource_name=INDEX_KEY_TYPE,
                                     property_name='local_indexes.{0}'.format(
                                         INDEX_KEY_TYPE),
                                     property_value=index_key_type_value)
            if index_key_type_value not in dynamodb_valid_key_types:
                raise AssertionError(
                    'Local Index hash key type of Table {0} '
                    'is unsupported by DynamoDB. Valid types are {1}'.format(
                        table_name, dynamodb_valid_key_types))

            # LSI hash key must be equal to table's hash key
            table_hash_key_name = table_meta[HASH_KEY_NAME]
            if index_key_name != table_hash_key_name or \
                    index_key_type_value != hash_key_type:
                raise AssertionError(
                    'Hash key name and type of LocalSecondaryIndex named {0}'
                    ' must be equal to Table\'s {1} one. Expected: {2}:{3}; '
                    'Actual: {4}:{5}'.format(index_name,
                                             table_name,
                                             table_hash_key_name,
                                             hash_key_type,
                                             index_key_name,
                                             index_key_type_value))

            index_sort_key_name = index.get(INDEX_SORT_KEY_NAME)
            assert_required_property(resource_name=INDEX_SORT_KEY_NAME,
                                     property_name='local_indexes.{0}'.format(
                                         INDEX_SORT_KEY_NAME),
                                     property_value=index_sort_key_name)
            index_sort_key_type_value = index.get(INDEX_SORT_KEY_TYPE)
            assert_required_property(resource_name=INDEX_SORT_KEY_TYPE,
                                     property_name='local_indexes.{0}'.format(
                                         INDEX_SORT_KEY_TYPE),
                                     property_value=index_sort_key_type_value)

            if index_sort_key_type_value not in dynamodb_valid_key_types:
                raise AssertionError(
                    'Local Index sort key type of Table {0} '
                    'is unsupported by DynamoDB. Valid types are {1}'.format(
                        table_name, dynamodb_valid_key_types))
            # LSI hash key must be equal to table's hash key
            if table_meta.get(SORT_KEY_NAME):
                if index_sort_key_name == table_meta[SORT_KEY_NAME]:
                    raise AssertionError(
                        'Sort key name of LocalSecondaryIndex '
                        'named {0} is equal to Table\'s {1} ones. '
                        'Sort key of LSI must differ from table\s. '
                        'Value: {2}'.format(
                            index_name,
                            table_name,
                            index_sort_key_name
                        ))


def _assert_key(meta, res_name, key_name_attr, key_type_attr):
    key_value = meta.get(key_name_attr)
    assert_required_property(resource_name=res_name,
                             property_name=key_name_attr,
                             property_value=key_value)
    key_type_value = meta.get(key_type_attr)
    assert_required_property(resource_name=res_name,
                             property_name=key_type_attr,
                             property_value=key_type_value)


def validate_dax_cluster(cluster_name: str, cluster_meta: dict):
    cluster_name = cluster_name.lower()
    parameter_type_mapping = {
        'node_type': str,
        'iam_role_name': str,
        'replication_factor': int,
        'subnet_group_name': str,
        'security_group_ids': list,
        'subnet_ids': list,
        'cluster_endpoint_encryption_type': str,
        'parameter_group_name': str,
        'availability_zones': list
    }

    errors = []
    if not (1 <= len(cluster_name) <= 20):
        errors.append(f'Cluster name \'{cluster_name}\' must be between '
                      f'1 and 20 characters but not {len(cluster_name)};')
    invalid_characters = re.findall('[^a-z0-9-]', cluster_name)
    if invalid_characters:
        errors.append(f'Cluster name \'{cluster_name}\' contains invalid '
                      f'characters: {invalid_characters};')

    for param in {'node_type', 'iam_role_name', 'replication_factor'}:
        if not cluster_meta.get(param):
            errors.append(f'Param \'{param}\' is required for a Dax cluster;')

    subnet_group_name = cluster_meta.get('subnet_group_name')
    subnet_ids = cluster_meta.get('subnet_ids')
    if subnet_ids and not subnet_group_name:
        errors.append('You must specify \'subnet_group_name\' if you '
                      'specify \'subnet_ids\'')

    for key, value_type in parameter_type_mapping.items():
        value = cluster_meta.get(key)
        if value and not isinstance(value, value_type):
            errors.append(f'Parameter \'{key}\' must have type '
                          f'\'{value_type.__name__}\' instead '
                          f'of {type(value).__name__};')
    encryption_type = cluster_meta.get('cluster_endpoint_encryption_type')
    if encryption_type and encryption_type not in ['NONE', 'TLS']:
        errors.append('Cluster endpoint encryption type must be either '
                      f'\'NONE\' or \'TLS\' but not \'{encryption_type}\'. '
                      f'By default it is \'TLS\'')
    if errors:
        errors_string = '\n'.join(errors)
        click.echo(f'Errors occurred during Dax cluster meta '
                   f'validation:\n{errors_string}')
        sys.exit(1)
