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
from syndicate.core import CONN
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.alarm_resource import remove_alarms
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')
_DYNAMO_DB_CONN = CONN.dynamodb()
_CW_METRIC = CONN.cw_metric()
_APP_AS_CONN = CONN.application_autoscaling()


def create_tables_by_10(args):
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
            response.update(_create_dynamodb_table_from_meta(name, meta))
            table = _DYNAMO_DB_CONN.get_table_by_name(name)
            waiters[table.name] = table.meta.client.get_waiter('table_exists')
        for table_name in waiters:
            waiters[table_name].wait(TableName=table_name)
        start = end
        end += 9
    return response


def _describe_table(name, meta, response):
    arn = response['TableArn']
    del response['TableArn']
    return {
        arn: build_description_obj(response, name, meta)
    }


def describe_stream(name, meta):
    response = _DYNAMO_DB_CONN.describe_table(meta['table'])
    res_obj = {
        'StreamSpecification': response['StreamSpecification'],
        'LatestStreamLabel': response['LatestStreamLabel']
    }
    arn = response['LatestStreamArn']
    return {
        arn: build_description_obj(res_obj, name, meta)
    }


def _create_dynamodb_table_from_meta(name, meta):
    """ Create Dynamo DB table from meta description after parameter
    validation.

    :type name: str
    :type meta: dict
    """
    required_parameters = ['hash_key_name', 'hash_key_type', 'read_capacity',
                           'write_capacity']
    validate_params(name, meta, required_parameters)

    res = _DYNAMO_DB_CONN.describe_table(name)
    autoscaling_config = meta.get('autoscaling')
    if res:
        _LOG.warn('%s table exists.', name)
        if autoscaling_config:
            res['Autoscaling'] = _describe_autoscaling(autoscaling_config,
                                                       name)
        return _describe_table(name, meta, res)

    _DYNAMO_DB_CONN.create_table(
        name, meta['hash_key_name'], meta['hash_key_type'],
        meta.get('sort_key_name'), meta.get('sort_key_type'),
        meta['read_capacity'], meta['write_capacity'],
        global_indexes=meta.get('global_indexes'), wait=False)
    response = _DYNAMO_DB_CONN.describe_table(name)
    if not response:
        raise AssertionError('Table with name {0} has not been created!'
                             .format(name))
    if autoscaling_config:
        _LOG.debug('Found autoscaling configuration for resource %s', name)
        sc_res = _enable_autoscaling(autoscaling_config, name)
        response['Autoscaling'] = sc_res
    _LOG.info('Created table %s.', name)
    return _describe_table(name, meta, response)


def _describe_autoscaling(autoscaling_config, name):
    targets = []
    policies = []
    for item in autoscaling_config:
        dimension = item['dimension']
        resource_name = item['resource_name']
        resource_id = _build_res_id(dimension, resource_name, name)
        sc_targets = _APP_AS_CONN.describe_scalable_targets(
            service_namespace='dynamodb',
            resources_ids=[resource_id],
            scalable_dimension=dimension)
        targets.extend(sc_targets)
        autoscaling_policy = item.get('config')
        if autoscaling_policy:
            policy_name = autoscaling_policy['policy_name']
            sc_policies = _APP_AS_CONN.describe_scaling_policies(
                service_namespace='dynamodb', policy_names=[policy_name],
                resource_id=resource_id, scalable_dimension=dimension)
            policies.extend(sc_policies)
    return {
        'targets': targets,
        'policies': policies
    }


def _enable_autoscaling(autoscaling_config, name):
    targets = []
    policies = []
    for item in autoscaling_config:
        autoscaling_required_parameters = ['resource_name', 'dimension',
                                           'min_capacity', 'max_capacity',
                                           'role_name']
        validate_params(name, item, autoscaling_required_parameters)
        role_name = item['role_name']
        role_arn = CONN.iam().check_if_role_exists(role_name)
        if role_arn:
            dimension = item['dimension']
            resource_id, sc_targets = register_autoscaling_target(dimension,
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
                sc_policies = put_autoscaling_policy(autoscaling_policy,
                                                     dimension, policy_name,
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


def put_autoscaling_policy(autoscaling_policy, dimension, policy_name,
                           resource_id):
    target_utilization = autoscaling_policy['target_utilization']
    scale_in_cooldown = autoscaling_policy.get('scale_in_cooldown')
    scale_out_cooldown = autoscaling_policy.get('scale_out_cooldown')
    metric_type = 'DynamoDBWriteCapacityUtilization' if 'Write' in dimension \
        else 'DynamoDBReadCapacityUtilization'
    response = _APP_AS_CONN.put_target_scaling_policy(
        policy_name=policy_name, service_namespace='dynamodb',
        resource_id=resource_id, scalable_dimension=dimension,
        target_value=target_utilization, predefined_metric_type=metric_type,
        scale_in_cooldown=scale_in_cooldown,
        scale_out_cooldown=scale_out_cooldown)
    return response


def register_autoscaling_target(dimension, item, role_arn, table_name):
    resource_name = item['resource_name']
    resource_id = _build_res_id(dimension, resource_name, table_name)
    _APP_AS_CONN.register_target(service_namespace='dynamodb',
                                 resource_id=resource_id,
                                 scalable_dimension=dimension,
                                 min_capacity=str(item['min_capacity']),
                                 max_capacity=str(item['max_capacity']),
                                 role_arn=role_arn)
    targets = _APP_AS_CONN.describe_scalable_targets(
        service_namespace='dynamodb',
        resources_ids=[resource_id],
        scalable_dimension=dimension)
    return resource_id, targets


def _build_res_id(dimension, resource_name, table_name):
    resource_id = 'table/{0}'.format(table_name) if 'table' in dimension \
        else 'table/{0}/index/{1}'.format(table_name, resource_name)
    return resource_id


def create_dynamodb_stream(args):
    """ Create Dynamo DB table streams in sub processes.

    :type args: list
    """
    create_pool(_create_dynamodb_stream_from_meta, 5, args)


@unpack_kwargs
def _create_dynamodb_stream_from_meta(name, meta):
    """ Enable Dynamo DB table stream if it is disabled.

    :type name: str
    :type meta: dict
    """
    required_parameters = ['table', 'stream_view_type']
    validate_params(name, meta, required_parameters)
    table_name = meta['table']

    stream = _DYNAMO_DB_CONN.get_table_stream_arn(table_name)
    if stream:
        _LOG.warn('Stream %s exists.', name)
        return

    try:
        _DYNAMO_DB_CONN.enable_table_stream(table_name,
                                            meta['stream_view_type'])
    except ClientError as e:
        # handle specific case for fantom stream enabling
        if 'ResourceInUseException' in e.message:
            _LOG.warn('Stream enabling currently in progress, table: %s',
                      table_name)
        else:
            raise e


def remove_dynamodb_tables(args):
    db_names = map(lambda x: x['config']['resource_name'], args)
    _DYNAMO_DB_CONN.remove_tables_by_names(db_names)
    _LOG.info('Dynamo DB tables %s were removed', str(db_names))
    alarm_args = []
    for arg in args:
        autoscaling = arg['config']['description'].get('Autoscaling')
        if autoscaling:
            policies = autoscaling['policies']
            for policy in policies:
                alarms = policy.get('Alarms', [])
                alarm_args.extend(map(lambda x: {
                    'arn': x['AlarmARN'],
                    'config': {'resource_name': x['AlarmName']}
                }, alarms))

    remove_alarms(alarm_args)
