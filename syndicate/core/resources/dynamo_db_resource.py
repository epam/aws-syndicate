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
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.resources.abstract_external_resource import AbstractExternalResource
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

AUTOSCALING_REQUIRED_PARAMS = ['resource_name', 'dimension',
                               'min_capacity', 'max_capacity',
                               'role_name']

DYNAMODB_TABLE_REQUIRED_PARAMS = ['hash_key_name', 'hash_key_type']

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')


class DynamoDBResource(AbstractExternalResource, BaseResource):

    def __init__(self, dynamodb_conn, cw_alarm_conn,
                 app_as_conn, iam_conn) -> None:
        self.dynamodb_conn = dynamodb_conn
        self.cw_alarm_conn = cw_alarm_conn
        self.app_autoscaling_conn = app_as_conn
        self.iam_conn = iam_conn

    def create_tables(self, args, step=10):
        """ Only 10 tables can be created, updated or deleted simultaneously.

        :param args: list of tables configurations meta
        :type args: list
        :param step: how many tables to create simultaneously
        :type step: int
        :returns tables create results as list
        """
        response = dict()
        waiters = {}
        tables_chunks = [args[i:i + step] for i in range(0, len(args), step)]
        for tables_to_create in tables_chunks:
            for table in tables_to_create:
                name = table['name']
                meta = table['meta']
                response.update(
                    self._create_dynamodb_table_from_meta(name, meta))
                table = self.dynamodb_conn.get_table_by_name(name)
                waiters[table.name] = table.meta.client.get_waiter(
                    'table_exists')
            for table_name in waiters:
                waiters[table_name].wait(TableName=table_name)
        return response

    def update_tables(self, args, step=10):
        """ Only 10 tables can be created, updated or deleted simultaneously.

        :param args: list of tables configurations meta
        :type args: list
        :param step: how many tables to update simultaneously
        :type step: int
        :returns tables update results as list
        """
        response = dict()
        tables_chunks = [args[i:i + step] for i in range(0, len(args), step)]
        for tables_to_update in tables_chunks:
            for table in tables_to_update:
                name = table['name']
                meta = table['meta']
                response.update(
                    self._update_dynamodb_table_from_meta(name, meta))
        return response

    @staticmethod
    def _determine_table_capacity_mode(table):
        existing_read_capacity = \
            table.provisioned_throughput.get('ReadCapacityUnits')
        existing_write_capacity = \
            table.provisioned_throughput.get('WriteCapacityUnits')
        if existing_read_capacity and existing_write_capacity:
            return 'PROVISIONED'
        return 'PAY_PER_REQUEST'

    def _update_dynamodb_table_from_meta(self, name, meta):
        """ Update Dynamo DB table from meta description, specifically:
        capacity (billing) mode, table or gsi capacity units,
        gsi to create or delete, ttl.

        :param name: DynamoDB table name
        :type name: str
        :param meta: table configuration information
        :type meta: dict
        :returns table update result as dict
        """
        table = self.dynamodb_conn.get_table_by_name(name)
        if not table:
            raise AssertionError('{0} table does not exist.'.format(name))

        existing_capacity_mode = self._determine_table_capacity_mode(table)
        response = self.dynamodb_conn.update_table_capacity(
            table_name=name,
            existing_capacity_mode=existing_capacity_mode,
            read_capacity=meta.get('read_capacity'),
            write_capacity=meta.get('write_capacity'),
            existing_read_capacity=
                table.provisioned_throughput.get('ReadCapacityUnits'),
            existing_write_capacity=
                table.provisioned_throughput.get('WriteCapacityUnits'),
            existing_global_indexes=table.global_secondary_indexes or []
        )
        if response:
            table = response

        self.dynamodb_conn.update_table_ttl(
            table_name=name,
            ttl_attribute_name=meta.get('ttl_attribute_name')
        )

        existing_capacity_mode = self._determine_table_capacity_mode(table)
        global_indexes_meta = meta.get('global_indexes', [])
        self.dynamodb_conn.update_global_indexes(
            table_name=name,
            global_indexes_meta=global_indexes_meta,
            existing_global_indexes=table.global_secondary_indexes or [],
            table_read_capacity=
                table.provisioned_throughput.get('ReadCapacityUnits'),
            table_write_capacity=
                table.provisioned_throughput.get('WriteCapacityUnits'),
            existing_capacity_mode=existing_capacity_mode
        )

        return self.describe_table(name, meta)

    def describe_table(self, name, meta, response=None):
        if not response:
            response = self.dynamodb_conn.describe_table(table_name=name)
        arn = response['TableArn']
        del response['TableArn']
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_stream(self, name, meta):
        response = self.dynamodb_conn.describe_table(meta['table'])
        res_obj = {
            'StreamSpecification': response['StreamSpecification'],
            'LatestStreamLabel': response['LatestStreamLabel']
        }
        arn = response['LatestStreamArn']
        return {
            arn: build_description_obj(res_obj, name, meta)
        }

    def describe_meta(self, name):
        meta = {
            'resource_type': 'dynamodb_table',
            'external': True
        }
        response = self.dynamodb_conn.describe_table(table_name=name)

        if not response:
            return {}

        key_schema = {k['KeyType']: k['AttributeName'] for k in response['KeySchema']}
        attribute_definitions = {k['AttributeName']: k['AttributeType'] for k in response['AttributeDefinitions']}

        hash_key_name = key_schema.get('HASH')
        hash_key_type = attribute_definitions[hash_key_name] if hash_key_name else None

        sort_key_name = key_schema.get('RANGE')
        sort_key_type = attribute_definitions[sort_key_name] if sort_key_name else None

        meta.update({
            'hash_key_name': hash_key_name,
            'hash_key_type': hash_key_type,
            'sort_key_name': sort_key_name,
            'sort_key_type': sort_key_type,
        })

        gsi = response.get('GlobalSecondaryIndexes')
        if gsi:
            global_indexes = []
            for index in gsi:
                key_schema = {k['KeyType']: k['AttributeName'] for k in index['KeySchema']}

                index_key_name = key_schema.get('HASH')
                index_key_type = attribute_definitions.get(index_key_name) if index_key_name else None

                sort_key_name = key_schema.get('RANGE')
                sort_key_type = attribute_definitions.get(sort_key_name) if sort_key_name else None

                index_data = {
                    'name': index.get('IndexName'),
                    'index_key_name': index_key_name,
                    'index_key_type': index_key_type,
                    'index_sort_key_name': sort_key_name,
                    'index_sort_key_type': sort_key_type,
                }
                global_indexes.append(index_data)
            global_indexes.sort(key=lambda k:k['name'])
            meta['global_indexes'] = global_indexes

        return {name: meta}

    def define_resource_shape(self):
        return {
            'resource_type': None,
            'hash_key_name': None,
            'hash_key_type': None,
            'sort_key_name': None,
            'sort_key_type': None,
            'global_indexes': [
                {
                    'name': None,
                    'index_key_name': None,
                    'index_key_type': None,
                    'sort_key_name': None,
                    'sort_key_type': None,
                    'index_sort_key_name': None,
                    'index_sort_key_type': None
                }
            ]
        }

    def _create_dynamodb_table_from_meta(self, name, meta):
        """ Create Dynamo DB table from meta description after parameter
        validation.
    
        :type name: str
        :type meta: dict
        """
        validate_params(name, meta, DYNAMODB_TABLE_REQUIRED_PARAMS)

        res = self.dynamodb_conn.describe_table(name)
        autoscaling_config = meta.get('autoscaling')
        if res:
            _LOG.warn('%s table exists.', name)
            if autoscaling_config:
                res['Autoscaling'] = self._describe_autoscaling(
                    autoscaling_config,
                    name)
            response = self.describe_table(name, meta, res)
            arn = list(response.keys())[0]
            response[arn]['resource_meta']['external'] = True
            return response

        self.dynamodb_conn.create_table(
            name, meta['hash_key_name'], meta['hash_key_type'],
            meta.get('sort_key_name'), meta.get('sort_key_type'),
            meta.get('read_capacity'), meta.get('write_capacity'),
            global_indexes=meta.get('global_indexes'),
            local_indexes=meta.get('local_indexes'),
            wait=True)
        response = self.dynamodb_conn.describe_table(name)
        if not response:
            raise AssertionError('Table with name {0} has not been created!'
                                 .format(name))
        # enabling stream if present
        stream_view_type = meta.get('stream_view_type')
        if stream_view_type:
            stream = self.dynamodb_conn.get_table_stream_arn(name)
            if stream:
                _LOG.warn('Stream %s exists.', name)
            else:
                try:
                    self.dynamodb_conn.enable_table_stream(name,
                                                           stream_view_type)
                except ClientError as e:
                    # handle specific case for fantom stream enabling
                    if 'ResourceInUseException' in str(e):
                        _LOG.warn('Stream enabling currently in progress,'
                                  ' table: %s', name)
                    else:
                        raise e
        if autoscaling_config:
            _LOG.debug('Found autoscaling configuration for resource %s', name)
            sc_res = self._enable_autoscaling(autoscaling_config, name)
            response['Autoscaling'] = sc_res
        _LOG.info('Created table %s.', name)
        return self.describe_table(name, meta, response)

    def _describe_autoscaling(self, autoscaling_config, name):
        targets = []
        policies = []
        for item in autoscaling_config:
            dimension = item['dimension']
            resource_name = item['resource_name']
            resource_id = self.build_res_id(dimension, resource_name, name)
            sc_targets = self.app_autoscaling_conn.describe_scalable_targets(
                service_namespace='dynamodb',
                resources_ids=[resource_id],
                scalable_dimension=dimension)
            targets.extend(sc_targets)
            autoscaling_policy = item.get('config')
            if autoscaling_policy:
                policy_name = autoscaling_policy['policy_name']
                sc_policies = self.app_autoscaling_conn.describe_scaling_policies(
                    service_namespace='dynamodb', policy_names=[policy_name],
                    resource_id=resource_id, scalable_dimension=dimension)
                policies.extend(sc_policies)
        return {
            'targets': targets,
            'policies': policies
        }

    def _enable_autoscaling(self, autoscaling_config, name):
        targets = []
        policies = []
        for item in autoscaling_config:
            validate_params(name, item, AUTOSCALING_REQUIRED_PARAMS)
            role_name = item['role_name']
            role_arn = self.iam_conn.check_if_role_exists(role_name)
            if role_arn:
                dimension = item['dimension']
                resource_id, sc_targets = self.register_autoscaling_target(
                    dimension,
                    item,
                    role_arn,
                    name)
                targets.extend(sc_targets)
                _LOG.debug('Autoscaling %s is set up for %s', dimension,
                           resource_id)
                autoscaling_policy = item.get('config')
                if autoscaling_policy:
                    policy_name = autoscaling_policy['policy_name']
                    _LOG.debug('Going to set up autoscaling with '
                               'policy %s', policy_name)
                    sc_policies = self.put_autoscaling_policy(
                        autoscaling_policy,
                        dimension,
                        policy_name,
                        resource_id)
                    policies.append(sc_policies)
                    _LOG.debug('Policy %s is set up', policy_name)
            else:
                _LOG.warn('Role %s is not found, skip autoscaling config',
                          role_name)
        return {
            'targets': targets,
            'policies': policies
        }

    def put_autoscaling_policy(self, autoscaling_policy, dimension,
                               policy_name,
                               resource_id):
        target_utilization = autoscaling_policy['target_utilization']
        scale_in_cooldown = autoscaling_policy.get('scale_in_cooldown')
        scale_out_cooldown = autoscaling_policy.get('scale_out_cooldown')
        metric_type = 'DynamoDBWriteCapacityUtilization' \
            if 'Write' in dimension \
            else 'DynamoDBReadCapacityUtilization'
        response = self.app_autoscaling_conn.put_target_scaling_policy(
            policy_name=policy_name, service_namespace='dynamodb',
            resource_id=resource_id, scalable_dimension=dimension,
            target_value=target_utilization,
            predefined_metric_type=metric_type,
            scale_in_cooldown=scale_in_cooldown,
            scale_out_cooldown=scale_out_cooldown)
        return response

    def register_autoscaling_target(self, dimension, item, role_arn,
                                    table_name):
        resource_name = item['resource_name']
        resource_id = self.build_res_id(dimension, resource_name, table_name)
        self.app_autoscaling_conn.register_target(service_namespace='dynamodb',
                                                  resource_id=resource_id,
                                                  scalable_dimension=dimension,
                                                  min_capacity=str(
                                                      item['min_capacity']),
                                                  max_capacity=str(
                                                      item['max_capacity']),
                                                  role_arn=role_arn)
        targets = self.app_autoscaling_conn.describe_scalable_targets(
            service_namespace='dynamodb',
            resources_ids=[resource_id],
            scalable_dimension=dimension)
        return resource_id, targets

    @staticmethod
    def build_res_id(dimension, resource_name, table_name):
        resource_id = 'table/{0}'.format(table_name) \
            if 'table' in dimension \
            else 'table/{0}/index/{1}'.format(table_name, resource_name)
        return resource_id

    def remove_dynamodb_tables(self, args):
        db_names = [x['config']['resource_name'] for x in args]
        self.dynamodb_conn.remove_tables_by_names(db_names)
        _LOG.info('Dynamo DB tables %s were removed', str(db_names))
        alarm_args = []
        for arg in args:
            autoscaling = arg['config']['description'].get('Autoscaling')
            if autoscaling:
                policies = autoscaling['policies']
                for policy in policies:
                    if policy:
                        alarms = policy.get('Alarms', [])
                        alarm_args.extend(map(lambda x: {
                            'arn': x['AlarmARN'],
                            'config': {'resource_name': x['AlarmName']}
                        }, alarms))

        self.cw_alarm_conn.remove_alarms(alarm_args)
