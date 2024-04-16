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
import time
from operator import itemgetter

from boto3 import client, resource
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry


_LOG = get_logger('syndicate.connection.dynamo_connection')

DEFAULT_READ_CAPACITY = DEFAULT_WRITE_CAPACITY = 5


def _append_attr_definition(definition, attr_name, attr_type):
    """ Adds an attribute definition if it is not already present.
    Dynamodb table creation requires to define attributes that are keys
    for the table or indexes. There must be no duplicated attribute
    definitions - aws throws ValidationException in such case.

    :type definition: []
    :type attr_name: str
    :type attr_type: str
    """
    for each in definition:
        if each['AttributeName'] == attr_name:
            return  # attribute is already defined, must not duplicate
    definition.append(dict(AttributeName=attr_name,
                           AttributeType=attr_type))


def _build_global_index_definition(index, read_throughput=1,
                                   write_throughput=1):
    index_info = _build_index_definition(index)
    index_info['ProvisionedThroughput'] = {
        'ReadCapacityUnits': read_throughput,
        'WriteCapacityUnits': write_throughput
    }
    return index_info


def _add_index_keys_to_definition(definition, index):
    _append_attr_definition(definition, index["index_key_name"],
                            index["index_key_type"])
    if index.get('index_sort_key_name'):
        _append_attr_definition(definition,
                                index["index_sort_key_name"],
                                index["index_sort_key_type"])


def _build_index_definition(index):
    """
    Creates request object to Index to be deployed
    :param index:
    :return:
    """
    index_def = {
        "IndexName": index["name"],
        "KeySchema": [
            {
                "AttributeName": index["index_key_name"],
                "KeyType": "HASH"
            }
        ],
        "Projection": {
            "ProjectionType": "ALL"
        }
    }
    if index.get('index_sort_key_name'):
        index_def['KeySchema'].append(
            {
                "AttributeName": index["index_sort_key_name"],
                "KeyType": "RANGE"
            })
    return index_def


@apply_methods_decorator(retry())
class DynamoConnection(object):
    """ DynamoDB class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, endpoint=None,
                 aws_session_token=None):
        self.conn = resource("dynamodb", region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             endpoint_url=endpoint,
                             aws_session_token=aws_session_token)
        self.client = client("dynamodb", region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             endpoint_url=endpoint,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new DynamoDB connection.')

    def create_table(self, table_name, hash_key_name, hash_key_type,
                     sort_key_name=None, sort_key_type=None, read_throughput=None,
                     write_throughput=None, wait=True, global_indexes=None,
                     local_indexes=None):
        """ Table creation.

        :type table_name: str
        :type hash_key_name: str
        :type hash_key_type: N/S/B
        :type sort_key_name: str
        :type sort_key_type: N/S/B
        :type read_throughput: int
        :type write_throughput: int
        :type wait: bool
        :type global_indexes: dict
        :type local_indexes: dict
        :returns created table
        """
        params = dict()
        if not read_throughput and not write_throughput:
            _LOG.info('No write_capacity neither read_capacity are specified. '
                      'Setting on-demand mode')
            params['BillingMode'] = 'PAY_PER_REQUEST'
        else:
            _LOG.info('Read or/and write capacity are specified. '
                      'Using provisioned mode.')
            params['BillingMode'] = 'PROVISIONED'
            params['ProvisionedThroughput'] = dict(
                ReadCapacityUnits=read_throughput or DEFAULT_READ_CAPACITY,
                WriteCapacityUnits=write_throughput or DEFAULT_WRITE_CAPACITY)

        schema = [dict(AttributeName=hash_key_name, KeyType='HASH')]
        definition = [dict(AttributeName=hash_key_name,
                           AttributeType=hash_key_type)]
        stream = {'StreamEnabled': False}
        if sort_key_name:
            schema.append(dict(AttributeName=sort_key_name,
                               KeyType='RANGE'))
            definition.append(dict(AttributeName=sort_key_name,
                                   AttributeType=sort_key_type))
        if global_indexes:
            for index in global_indexes:
                _add_index_keys_to_definition(definition=definition,
                                              index=index)
        if local_indexes:
            for index in local_indexes:
                _add_index_keys_to_definition(definition=definition,
                                              index=index)
        params.update(dict(
            TableName=table_name, KeySchema=schema,
            AttributeDefinitions=definition, StreamSpecification=stream
        ))
        if global_indexes:
            params['GlobalSecondaryIndexes'] = []
            for index in global_indexes:
                index_info = _build_global_index_definition(index,
                                                            read_throughput,
                                                            write_throughput)
                params['GlobalSecondaryIndexes'].append(index_info)
        if local_indexes:
            params['LocalSecondaryIndexes'] = []
            for index in local_indexes:
                index_info = _build_index_definition(index)
                params['LocalSecondaryIndexes'].append(index_info)
        table = self.conn.create_table(**params)
        if wait:
            waiter = table.meta.client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
        return table

    def update_table_ttl(self, table_name, ttl_attribute_name, wait=True):
        """ Updates table ttl attribute

        :param table_name: DynamoDB table name
        :type table_name: str
        :param ttl_attribute_name: name of the table's attribute that holds
            ttl value
        :type ttl_attribute_name: str
        :param wait: to wait for table update to finish or not
        :type wait: bool
        :returns update_time_to_live response as dict
        """
        ttl_enabled = ttl_attribute_name is not None
        existing_ttl_specs = self.client.describe_time_to_live(
            TableName=table_name
        )['TimeToLiveDescription']
        existing_ttl_enabled = \
            existing_ttl_specs.get('TimeToLiveStatus') == 'ENABLED'
        existing_ttl_attribute_name = \
            existing_ttl_specs.get('AttributeName')

        if ttl_enabled != existing_ttl_enabled:
            _LOG.info(
                'Updating ttl value to {0} for table {1}, attribute name: {2}'
                .format(ttl_enabled, table_name, ttl_attribute_name))
            response = self.client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': ttl_enabled,
                    # set ttl attribute name to the one defined in meta when
                    # enabling ttl, otherwise, set existing ttl name
                    # when disabling
                    'AttributeName': ttl_attribute_name if ttl_enabled
                        else existing_ttl_attribute_name
                }
            )
            if wait:
                self._wait_for_table_update(table_name=table_name)
            return response

    def update_global_indexes(self, table_name, global_indexes_meta,
                              existing_global_indexes, table_read_capacity,
                              table_write_capacity, existing_capacity_mode):
        """ Creates, Deletes or Updates global indexes for the table

        :param table_name: DynamoDB table name
        :type table_name: str
        :param global_indexes_meta: list of global indexes definitions in meta
        :type global_indexes_meta: list
        :param existing_global_indexes: list of global indexes currently
            existing in table
        :type existing_global_indexes: list
        :param table_read_capacity: table read capacity defined in meta
        :type table_read_capacity: int
        :param table_write_capacity: table write capacity defined in meta
        :type table_write_capacity: int
        :param existing_capacity_mode: capacity mode currently set in the table
        :type existing_capacity_mode: str
        :returns None
        """
        gsi_names = [gsi.get('name') for gsi in global_indexes_meta]
        existing_gsi_names = [gsi.get('IndexName')
                              for gsi in existing_global_indexes]

        global_indexes_to_delete = []
        for gsi in existing_global_indexes:
            if gsi.get('IndexName') not in gsi_names:
                global_indexes_to_delete.append(gsi)

        global_indexes_to_create = []
        for gsi in global_indexes_meta:
            if gsi.get('name') not in existing_gsi_names:
                global_indexes_to_create.append(gsi)

        global_indexes_to_update_capacity = []
        # AWS handles changing gsi capacity mode from provisioned to on-demand,
        # so we don't have to
        if existing_capacity_mode == 'PROVISIONED':
            for gsi in global_indexes_meta:
                for existing_index in existing_global_indexes:
                    if gsi['name'] == existing_index['IndexName']:
                        existing_read_capacity = existing_index['ProvisionedThroughput']['ReadCapacityUnits']
                        existing_write_capacity = \
                            existing_index['ProvisionedThroughput']['WriteCapacityUnits']
                        read_capacity_meta = \
                            gsi.get('read_capacity') or table_read_capacity
                        write_capacity_meta = \
                            gsi.get('write_capacity') or table_write_capacity

                        # add indexes with different capacity values for update
                        if existing_read_capacity != read_capacity_meta \
                                or existing_write_capacity != write_capacity_meta:
                            gsi.update(
                                dict(old_read_capacity=existing_read_capacity,
                                     old_write_capacity=existing_write_capacity))
                            global_indexes_to_update_capacity.append(gsi)
                        break

        for gsi in global_indexes_to_delete:
            index_name = gsi.get('IndexName')
            self.delete_global_secondary_index(table_name=table_name,
                                               index_name=index_name)
            self._wait_for_index_update(table_name, index_name)
            _LOG.info(
                'Removed global secondary index {0} for table {1}'.format(
                    index_name, table_name))

        for gsi in global_indexes_to_create:
            read_capacity = \
                gsi.get('read_capacity') or table_read_capacity
            write_capacity = \
                gsi.get('write_capacity') or table_write_capacity
            self.create_global_secondary_index(
                table_name=table_name, index_meta=gsi,
                existing_capacity_mode=existing_capacity_mode,
                read_throughput=read_capacity, write_throughput=write_capacity)
            self._wait_for_index_update(table_name, gsi.get('name'))
            _LOG.info(
                'Created global secondary index {0} for table {1}'.format(
                    gsi.get('name'), table_name))

        for gsi in global_indexes_to_update_capacity:
            read_capacity = \
                gsi.get('read_capacity') or table_read_capacity
            write_capacity = \
                gsi.get('write_capacity') or table_write_capacity
            self.update_global_secondary_index(
                table_name=table_name, index_name=gsi.get('name'),
                read_throughput=read_capacity, write_throughput=write_capacity)
            _LOG.info(
                'Updated global secondary index {0} for table {1}. '
                'Updated read capacity from {2} to {3}, '
                'write capacity from {4} to {5}'.format(
                    gsi.get('name'), table_name,
                    gsi.get('old_read_capacity'), read_capacity,
                    gsi.get('old_write_capacity'), write_capacity))

    def _wait_for_table_update(self, table_name, sleep_amount=20,
                               max_attempts=25):
        """ Waits for table to go into ACTIVE state.

        :param table_name: DynamoDB table name
        :type table_name: str
        :param sleep_amount: time in seconds to wait for the next attempt
        :type sleep_amount: int
        :param max_attempts: maximum attempts to ping the table
        :type max_attempts: int
        :returns None
        """
        table = self.get_table_by_name(table_name)
        table.wait_until_exists(
            WaiterConfig={
                'Delay': sleep_amount,
                'MaxAttempts': max_attempts
            }
        )

    def _wait_for_index_update(self, table_name, index_name, sleep_amount=20,
                               max_attempts=25):
        """ Waits for global secondary index
        to be able to continue table update.

        :param table_name: DynamoDB table name
        :type table_name: str
        :param index_name: name of the global index to wait for
        :type index_name: str
        :param sleep_amount: time in seconds to wait for the next attempt
        :type sleep_amount: int
        :param max_attempts: maximum attempts to ping the table
        :type max_attempts: int
        :returns None
        """
        num_attempts = 0
        while True:
            num_attempts += 1
            table = self.describe_table(table_name)
            indexes = table.get('GlobalSecondaryIndexes', [])
            index = next(
                (idx for idx in indexes if idx['IndexName'] == index_name),
                None
            )
            # there is no index which means it was successfully deleted or
            # the index is in backfilling state which allows
            # to continue table update
            if index is None or index.get('Backfilling'):
                return
            if num_attempts >= max_attempts:
                raise AssertionError('Max attempts exceeded')
            time.sleep(sleep_amount)

    def delete_global_secondary_index(self, table_name, index_name):
        """ Deletes global secondary index from the specified table.

        :param table_name: DynamoDB table name
        :type table_name: str
        :param index_name: name of the global index to delete
        :type index_name: str
        :returns update_table response as dict
        """
        response = self.client.update_table(
            TableName=table_name,
            GlobalSecondaryIndexUpdates=[
                {
                    'Delete': {
                        'IndexName': index_name
                    }
                }
            ]
        )
        return response

    def create_global_secondary_index(self, table_name, index_meta,
                                      existing_capacity_mode,
                                      read_throughput=None,
                                      write_throughput=None):
        """ Creates global secondary index for the specified table.

        :param table_name: DynamoDB table name
        :type table_name: str
        :param index_meta: global index info defined in meta
        :type index_meta: dict
        :param existing_capacity_mode: capacity mode currently set in the table
        :type existing_capacity_mode: str
        :param read_throughput: read capacity to assign for global index
        :type read_throughput: int
        :param write_throughput: write capacity to assign for global index
        :type write_throughput: int
        :returns update_table response as dict
        """
        index_info = _build_global_index_definition(
            index=index_meta, read_throughput=read_throughput,
            write_throughput=write_throughput)
        definitions = []
        _add_index_keys_to_definition(definition=definitions, index=index_meta)
        if existing_capacity_mode == 'PAY_PER_REQUEST':
            index_info.pop('ProvisionedThroughput')
        response = self.client.update_table(
            TableName=table_name,
            AttributeDefinitions=definitions,
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': index_info
                }
            ]
        )
        return response

    def update_global_secondary_index(self, table_name, index_name,
                                      read_throughput=None,
                                      write_throughput=None):
        """ Updates global secondary index capacity for the specified table.

        :param table_name: DynamoDB table name
        :type table_name: str
        :param index_name: name of the index to update
        :type index_name: str
        :param read_throughput: read capacity to assign for global index
        :type read_throughput: int
        :param write_throughput: write capacity to assign for global index
        :type write_throughput: int
        :returns update_table response as dict
        """
        read_throughput = read_throughput or 1
        write_throughput = write_throughput or 1
        response = self.client.update_table(
            TableName=table_name,
            GlobalSecondaryIndexUpdates=[
                {
                    'Update': {
                        'IndexName': index_name,
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': read_throughput,
                            'WriteCapacityUnits': write_throughput
                        }
                    }
                }
            ]
        )
        return response

    def enable_table_stream(self, table_name,
                            stream_type='NEW_AND_OLD_IMAGES'):
        """ Sets StreamEnabled=true for the specified table.

        :type table_name: str
        :type stream_type: str
        """
        table = self.get_table_by_name(table_name)
        table.update(
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': stream_type
            }
        )

    def disable_table_stream(self, table_name,
                             stream_type='NEW_AND_OLD_IMAGES'):
        """ Sets StreamEnabled=false for the specified table.

        :type table_name: str
        :type stream_type: str
        """
        table = self.get_table_by_name(table_name)
        table.update(
            StreamSpecification={
                'StreamEnabled': False,
                'StreamViewType': stream_type
            }
        )

    def is_stream_enabled(self, table_name):
        table = self.get_table_by_name(table_name)
        stream = table.stream_specification
        if stream:
            return stream.get('StreamEnabled')

    def update_table_capacity(self, table_name, existing_capacity_mode,
                              read_capacity, write_capacity,
                              existing_read_capacity, existing_write_capacity,
                              existing_global_indexes, wait=True):
        """ Updates table capacity configuration. If both read_capacity and
        write capacity are provided in the deployment_resources.json
        sets their values for the table if it has PROVISIONED billing mode, if
        it is in the PAY_PER_REQUEST mode, the table is set to PROVISIONED with
        specified capacity values. If the capacity attributes are omitted and
        the table is in the PROVISIONED mode it is set to the PAY_PER_REQUEST.
        :param table_name: DynamoDB table name
        :type table_name: str
        :param existing_capacity_mode: capacity mode currently set in the table
        :type existing_capacity_mode: str
        :param read_capacity: read capacity to assign for the table
        :type read_capacity: int
        :param write_capacity: write capacity to assign for the table
        :type write_capacity: int
        :param existing_read_capacity: read capacity currently set in the table
        :type existing_read_capacity: int
        :param existing_write_capacity: write capacity currently set
            in the table
        :type existing_write_capacity: int
        :param existing_global_indexes: global secondary indexes already
            present in the table
        :type existing_global_indexes: list
        :param wait: to wait for table update to finish or not
        :type wait: bool
        :returns update_table response as boto3.DynamoDB.Table object or None
            if there were no changes made
        """
        params = {}
        if read_capacity and write_capacity:
            if existing_capacity_mode == 'PROVISIONED':
                if read_capacity != existing_read_capacity \
                        or write_capacity != existing_write_capacity:
                    params['ProvisionedThroughput'] = dict(
                        ReadCapacityUnits=read_capacity,
                        WriteCapacityUnits=write_capacity)
            elif existing_capacity_mode == 'PAY_PER_REQUEST':
                params['BillingMode'] = 'PROVISIONED'
                params['ProvisionedThroughput'] = dict(
                    ReadCapacityUnits=read_capacity,
                    WriteCapacityUnits=write_capacity)
                global_secondary_indexes_updates = []
                for gsi in existing_global_indexes:
                    gsi_read_capacity = \
                        gsi.get('ProvisionedThroughput', {}).get(
                            'ReadCapacityUnits') or read_capacity
                    gsi_write_capacity = \
                        gsi.get('ProvisionedThroughput', {}
                                ).get('WriteCapacityUnits') or write_capacity
                    global_secondary_indexes_updates.append({
                        'Update': {
                            'IndexName': gsi.get('IndexName'),
                            'ProvisionedThroughput': {
                                'ReadCapacityUnits': gsi_read_capacity,
                                'WriteCapacityUnits': gsi_write_capacity
                            }
                        }
                    })
                params['GlobalSecondaryIndexUpdates'] = \
                    global_secondary_indexes_updates
        else:
            if existing_capacity_mode == 'PROVISIONED':
                params['BillingMode'] = 'PAY_PER_REQUEST'

        if params:
            params.update(dict(TableName=table_name))
            _LOG.debug(f'Updating {table_name} table capacity. Table capacity '
                       f'mode: {existing_capacity_mode}, meta read/write '
                       f'capacities: {read_capacity}/{write_capacity}, existing '
                       f'read/write capacities: {existing_read_capacity}/'
                       f'{existing_write_capacity}. Update params: {params}')
            self.client.update_table(**params)
            if wait:
                self._wait_for_table_update(table_name=table_name)
            return self.get_table_by_name(table_name)

    def get_table_by_name(self, table_name):
        """ Get table by name.

        :type table_name: str
        :returns table
        """
        return self.conn.Table(table_name)

    def query_by_index(self, table_name, index_name, expression):
        table = self.get_table_by_name(table_name)
        return table.query(
            IndexName=index_name,
            KeyConditionExpression=expression
        )

    def query_by_index_and_expression(self, table_name, index_name, key,
                                      expression):
        table = self.get_table_by_name(table_name)
        return table.query(
            IndexName=index_name,
            KeyConditionExpression=key,
            FilterExpression=expression
        )

    def describe_table(self, table_name):
        try:
            return self.client.describe_table(TableName=table_name)['Table']
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                pass  # valid exception
            else:
                raise e

    def put_item(self, table_name, item):
        """ Creates a new item or updates existing in specified table.

        :type table_name: str
        :type item: dict
        """
        table = self.conn.Table(table_name)
        table.put_item(Item=item)

    def put_with_sort_by_date(self, resources_to_put, table_name):
        """ Saves billing records by date in ascending order

        :type resources_to_put: list
        :param resources_to_put: list with billing records

        :type table_name: str
        :param table_name: DynamoDB table name
        """
        for each in sorted(resources_to_put, key=itemgetter('d')):
            self.put_item(table_name, each)

    def items_batch_write(self, table_name, items):
        """ Write items to table from dict.

        :type table_name: str
        :type items: list
        """
        if items:
            table = self.conn.Table(table_name)
            with table.batch_writer() as batch:
                for each in items:
                    if isinstance(each, dict):
                        batch.put_item(Item=each)

    def items_batch_get(self, table_name, hash_key_name, hash_keys_values,
                        sort_key_name=None, sort_key_value=None):
        if hash_keys_values:
            hash_values_list = list()
            for hash_value in hash_keys_values:
                if sort_key_name and sort_key_value:
                    key = {
                        hash_key_name: hash_value,
                        sort_key_name: sort_key_value
                    }
                else:
                    key = {
                        hash_key_name: hash_value
                    }
                hash_values_list.append(key)
            results = []
            response = self.conn.batch_get_item(
                RequestItems={
                    table_name: {
                        'Keys': hash_values_list
                    }
                }
            )
            results.extend(response['Responses'][table_name])
            while response['UnprocessedKeys']:
                response = self.conn.batch_get_item(
                    RequestItems={
                        table_name: {
                            'Keys': hash_values_list
                        }
                    }
                )
                results.extend(response['Responses'][table_name])
            return results

    def get_item(self, table_name, hash_key_name, hash_key_value,
                 sort_key_name=None, sort_key_value=None):
        """ Get item from specified table by pk.

        :type table_name: str
        :type hash_key_name: str
        :param hash_key_value: str/number
        :type sort_key_name: str
        :param sort_key_value: str/number
        :returns list of items(if exists)
        """
        table = self.get_table_by_name(table_name)
        item = {hash_key_name: hash_key_value}
        if sort_key_name and sort_key_value:
            item[sort_key_name] = sort_key_value
        result = table.get_item(Key=item, ConsistentRead=True)
        if 'Item' in result:
            return result['Item']

    def scan(self, table_name=None, table=None, token=None,
             filter_expr=None, limit=None, attr_to_select='ALL_ATTRIBUTES'):
        """ DynamoDB table scan with consistent read and custom retry.

        :type table_name: str
        :type table: Table
        :type token: dict
        :type filter_expr: Attr
        :type limit: int
        :type attr_to_select: str
        """
        if table and table_name:
            raise ValueError("'table' OR 'table_name' must be set.")
        elif table:
            pass  # just use Table object
        elif table_name:
            table = self.get_table_by_name(table_name)
        else:
            raise ValueError("'table' or 'table_name' must be set.")

        params = {'ConsistentRead': True, 'Select': attr_to_select}
        if token:
            params['ExclusiveStartKey'] = token
        if filter_expr:
            params['FilterExpression'] = filter_expr
        if limit:
            params['Limit'] = limit

        return table.scan(**params)

    def get_all_items(self, table_name, filter_expr=None):
        """ Get all items from table.

        :type table_name: str
        :type filter_expr: Attr
        :return list(if items exist)
        """
        table = self.get_table_by_name(table_name)
        response = self.scan(table=table, filter_expr=filter_expr)
        do_continue = response.get('LastEvaluatedKey')
        items = []
        if 'Items' in response:
            items.extend(response['Items'])
        while do_continue:
            response = self.scan(table=table, token=do_continue,
                                 filter_expr=filter_expr)
            do_continue = response.get('LastEvaluatedKey')
            if 'Items' in response:
                items.extend(response['Items'])
        return items

    def _scan_all(self, table_name, func, limit=None, filter_expr=None, *args,
                  **kwargs):
        """ Calls a function for each item in the table.

        :type table_name: str
        :param func: Function to call for each item.
                     It must accept the item as the first argument.
        :type func: function
        :param args: any args the function takes after the item
        :param kwargs: any kwargs the func takes after the item and args
        """
        table = self.get_table_by_name(table_name)
        response = self.scan(table=table, filter_expr=filter_expr, limit=limit)
        do_continue = response.get('LastEvaluatedKey')
        if 'Items' in response:
            for each in response['Items']:
                func(each, *args, **kwargs)
        while do_continue:
            response = self.scan(table=table, token=do_continue, limit=limit,
                                 filter_expr=filter_expr)
            do_continue = response.get('LastEvaluatedKey')
            if 'Items' in response:
                for each in response['Items']:
                    func(each, *args, **kwargs)

    def for_each_item(self, table_name, func, *args, **kwargs):
        """ Go through all items in table and perform func.

        :type table_name: str
        :type func: function
        """
        self._scan_all(table_name, func, None, None, *args, **kwargs)

    def for_each_item_in_interval(self, start_interval, end_interval,
                                  interval_time, table_name, func,
                                  *args, **kwargs):
        """ Calls a function for each item in the table.

        :type start_interval: int (timestamp)
        :type end_interval: int (timestamp)
        :type interval_time: int (timestamp)
        :type table_name: str
        :param func: Function to call for each item.
                     It must accept the item as the first argument.
        :type func: function
        :param args: any args the function takes after the item
        :param kwargs: any kwargs the func takes after the item and args
        """
        table = self.get_table_by_name(table_name)
        start = start_interval
        count = 0
        while start < end_interval:
            response = self.scan(table=table,
                                 filter_expr=Attr('d').eq(start))
            do_continue = response.get('LastEvaluatedKey')
            if 'Items' in response:
                for each in response['Items']:
                    count += 1
                    func(each, *args, **kwargs)
            while do_continue:
                response = self.scan(table=table, token=do_continue,
                                     filter_expr=Attr('d').eq(start))
                do_continue = response.get('LastEvaluatedKey')
                if 'Items' in response:
                    for each in response['Items']:
                        count += 1
                        func(each, *args, **kwargs)
            start += interval_time

    def get_items_with_attribute_contains(self, table_name, attr_name, val):
        """ Get all items from table, which have specified attribute.

        :type table_name: str
        :type attr_name: str
        :type val: any
        :return list(if items exist)
        """
        return self.get_all_items(table_name, Attr(attr_name).contains(val))

    def get_items_with_attribute_value(self, table_name, attr_name,
                                       attr_value):
        """ Get all items from table, which have specified attribute with
        specified value.

        :type table_name: str
        :type attr_name: str
        :param attr_value: attr value in table
        :return: list(if items exist)
        """
        table = self.get_table_by_name(table_name)
        result = []
        response = self.scan(table=table,
                             filter_expr=Attr(attr_name).eq(attr_value))
        do_continue = response.get('LastEvaluatedKey')
        if 'Items' in response:
            result.extend(response['Items'])
        while do_continue:
            response = self.scan(table=table, token=do_continue,
                                 filter_expr=Attr(attr_name).eq(attr_value))
            do_continue = response.get('LastEvaluatedKey')
            if 'Items' in response:
                result.extend(response['Items'])
        return result

    def get_items_with_attr_between(self, table_name, attr_name,
                                    start, end):
        """ Get all items from table, which have specified attribute
        with specified value.

        :type table_name: str
        :type attr_name: str
        :param start: start attr value for range in table
        :param end: end attr value for range in table
        :return: list(if items exist)
        """
        return self.get_all_items(table_name,
                                  Attr(attr_name).between(start, end))

    def update_item(self, table_name, hash_key_name, hash_key_value,
                    key_to_set, value_to_set, sort_key_name=None,
                    sort_key_value=None):
        """ Updates some key in existing document using SET operator.

        :type table_name: str
        :type hash_key_name: str
        :param hash_key_value: value of the primary hash key
        :type key_to_set: str
        :param value_to_set: new value to set for the key_to_set
        :type sort_key_name: str
        :param sort_key_value: value of the primary sort key, if exists
        """
        self.flexible_update_item(table_name, hash_key_name, hash_key_value,
                                  'SET #k = :v', {'#k': key_to_set},
                                  {':v': value_to_set}, sort_key_name,
                                  sort_key_value)

    def flexible_update_item(self, table_name, hash_key_name, hash_key_value,
                             update_expression, expr_names, expr_values,
                             sort_key_name=None, sort_key_value=None):
        """ Updates some key in existing document using SET operator.

        :type table_name: str
        :param table_name: The name of the table.
        :type hash_key_name: str
        :param hash_key_name: name of the primary hash key
        :param hash_key_value: value of the primary hash key
        :type update_expression: str
        :param update_expression: Update expression with placeholders.
        :type expr_names: dict
        :param expr_names: expression attribute names
        :type expr_values: dict
        :param expr_values: expression attribute values
        :type sort_key_name: str
        :param sort_key_name: name of the primary sort key, if exists
        :param sort_key_value: value of the primary sort key, if exists
        """
        table = self.get_table_by_name(table_name)
        hash_key = {hash_key_name: hash_key_value}
        if sort_key_name and sort_key_value:
            hash_key[sort_key_name] = sort_key_value
        table.update_item(Key=hash_key, UpdateExpression=update_expression,
                          ExpressionAttributeNames=expr_names,
                          ExpressionAttributeValues=expr_values)

    def remove_specified_tables(self, table_names):
        """ Only 10 tables can be created, updated or deleted simultaneously.

        :type table_names: list of strings
        """
        waiters = {}
        start = 0
        end = 9
        while start < table_names:
            for name in table_names[:9]:
                table = self.get_table_by_name(name)
                waiters[table.name] = table.meta.client.get_waiter(
                    'table_not_exists')
                table.delete()
            for table_name in waiters:
                waiters[table_name].wait(TableName=table_name)

            start = end
            end += 9

    def table_exists(self, table_name):
        """ Check if table exists.

        :type table_name: str
        :return boolean
        """
        if table_name in self.get_tables_list():
            return True

    def get_table_stream_arn(self, table_name):
        """ Get table stream arn.

        :type table_name: str
        :return str(table stream name)
        """
        table = self.get_table_by_name(table_name)
        return table.latest_stream_arn

    def get_tables_list(self):
        """ Get all existing tables."""
        tables = []
        response = self.client.list_tables()
        token = response.get('LastEvaluatedTableName')
        tables.extend(response.get('TableNames'))
        while token:
            response = self.client.list_tables(ExclusiveStartTableName=token)
            token = response.get('LastEvaluatedTableName')
            tables.extend(response.get('TableNames'))
        return tables

    def remove_item(self, table_name, key_name, key_value, sort_name=None,
                    sort_value=None):
        """ Remove item from specified table by pk.

        :type table_name: str
        :type key_name: str
        :param key_value: value of attribute
        :type sort_name: str
        :param sort_value: value of attribute
        """
        table = self.get_table_by_name(table_name)
        key = {key_name: key_value}
        if sort_value and sort_name:
            key[sort_name] = sort_value
        table.delete_item(Key=key)

    def batch_remove_items(self, table_name, keys):
        table = self.get_table_by_name(table_name)
        with table.batch_writer() as batch:
            for key in keys:
                batch.delete_item(Key=key)

    def remove_table(self, table_name):
        """ Remove table and wait until AWS will perform operation.

        :type table_name: str
        """
        table = self.get_table_by_name(table_name)
        try:
            waiter = table.meta.client.get_waiter('table_not_exists')
            table.delete()
            waiter.wait(TableName=table_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Table %s is not found', table.name)
            else:
                raise e

    def remove_tables_by_names(self, table_names):
        """ Remove tables by names. AWS restricts simultaneous amount of
        tables, so after 10 requests sent we waiting when operations finish
        and then continue.

        :type table_names: list
        """
        waiters = {}
        count = 0
        while count < len(table_names):
            tables_to_remove = table_names[count: count + 9]
            for name in tables_to_remove:
                table = self.get_table_by_name(name)
                waiters[table.name] = table.meta.client.get_waiter(
                    'table_not_exists')
                try:
                    table.delete()
                except ClientError as e:
                    exception_type = e.response['Error']['Code']
                    if exception_type == 'ResourceNotFoundException':
                        _LOG.warn('Table %s is not found', table.name)
                    else:
                        raise e
            count += 9
            for table_name in waiters:
                waiters[table_name].wait(TableName=table_name)

    def _query(self, table_name=None, table=None, key_expr=None, token=None,
               limit=None, select='ALL_ATTRIBUTES'):
        if table and table_name:
            raise ValueError("'table' OR 'table_name' must be set.")
        elif table:
            pass  # just use Table object
        elif table_name:
            table = self.get_table_by_name(table_name)
        else:
            raise ValueError("'table' or 'table_name' must be set.")

        if not key_expr:
            raise ValueError("'key_expr' must be set.")

        params = {
            'ConsistentRead': True, 'Select': select,
            'KeyConditionExpression': key_expr
        }
        if token:
            params['ExclusiveStartKey'] = token
        if limit:
            params['Limit'] = limit

        return table.query(**params)

    def query(self, table, key_expr, limit=1):
        """ Finds all documents with provided hash key value, sorts them
        in descending order and returns the first document. Example:
        For:
        {hk: hk, sk: 1}
        {hk: hk, sk: 2}
        {hk: hk, sk: 3}
        Will return:
        {hk: hk, sk: 3}

        :param table: table name
        :type table: str
        :type limit: int
        :type key_expr: Key
        :return:
        """
        table = self.get_table_by_name(table)
        items = []
        res = self._query(table=table, limit=limit, key_expr=key_expr)
        do_continue = res.get('LastEvaluatedKey')
        if 'Items' in res:
            items.extend(res['Items'])
        while do_continue:
            res = self._query(table=table, limit=limit, key_expr=key_expr,
                              token=do_continue)
            do_continue = res.get('LastEvaluatedKey')
            if 'Items' in res:
                items.extend(res['Items'])
        return items

    def query_by_hash_key(self, table, hash_name, hash_value, limit=1):
        key_expr = Key(hash_name).eq(hash_value)
        return self.query(table, key_expr, limit)
