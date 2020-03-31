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
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')


class DynamoDBResource(BaseResource):

    def __init__(self, dynamodb_conn, cw_alarm_conn,
                 app_as_conn, iam_conn) -> None:
        self.dynamodb_conn = dynamodb_conn
        self.cw_alarm_conn = cw_alarm_conn
        self.app_autoscaling_conn = app_as_conn
        self.iam_conn = iam_conn

    def create_tables_by_10(self, args):
        """ Only 10 tables can be created, updated or deleted simultaneously.
    
        :type args: list
        """
        response = dict()
        waiters = {}
        start = 0
        end = 8
        while start < len(args):
            tables_to_create = args[start: end]
            for arg_set in tables_to_create:
                name = arg_set['name']
                meta = arg_set['meta']
                response.update(
                    self._create_dynamodb_table_from_meta(name, meta))
                table = self.dynamodb_conn.get_table_by_name(name)
                waiters[table.name] = table.meta.client.get_waiter(
                    'table_exists')
            for table_name in waiters:
                waiters[table_name].wait(TableName=table_name)
            start = end
            end += 9
        return response

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

    def _create_dynamodb_table_from_meta(self, name, meta):
        """ Create Dynamo DB table from meta description after parameter
        validation.
    
        :type name: str
        :type meta: dict
        """
        required_parameters = ['hash_key_name', 'hash_key_type',
                               'read_capacity',
                               'write_capacity']
        validate_params(name, meta, required_parameters)

        res = self.dynamodb_conn.describe_table(name)
        autoscaling_config = meta.get('autoscaling')
        if res:
            _LOG.warn('%s table exists.', name)
            if autoscaling_config:
                res['Autoscaling'] = self._describe_autoscaling(
                    autoscaling_config,
                    name)
            return self.describe_table(name, meta, res)

        self.dynamodb_conn.create_table(
            name, meta['hash_key_name'], meta['hash_key_type'],
            meta.get('sort_key_name'), meta.get('sort_key_type'),
            meta['read_capacity'], meta['write_capacity'],
            global_indexes=meta.get('global_indexes'),
            local_indexes=meta.get('local_indexes'),
            wait=False)
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
            resource_id = self._build_res_id(dimension, resource_name, name)
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
            autoscaling_required_parameters = ['resource_name', 'dimension',
                                               'min_capacity', 'max_capacity',
                                               'role_name']
            validate_params(name, item, autoscaling_required_parameters)
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
        resource_id = self._build_res_id(dimension, resource_name, table_name)
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

    def _build_res_id(self, dimension, resource_name, table_name):
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
