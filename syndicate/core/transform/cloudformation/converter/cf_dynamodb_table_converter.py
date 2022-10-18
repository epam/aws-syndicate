"""
    Copyright 2021 EPAM Systems, Inc.

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
from troposphere import applicationautoscaling as app_scaling
from troposphere import dynamodb

from syndicate.commons.log_helper import get_logger
from syndicate.connection.dynamo_connection import (
    DEFAULT_READ_CAPACITY, DEFAULT_WRITE_CAPACITY)
from syndicate.core.resources.dynamo_db_resource import (
    DYNAMODB_TABLE_REQUIRED_PARAMS, AUTOSCALING_REQUIRED_PARAMS,
    DynamoDBResource)
from syndicate.core.resources.helper import validate_params
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import (to_logic_name, iam_role_logic_name,
                                  dynamodb_table_logic_name)

_LOG = get_logger('cf_dynamodb_table_converter')


def _add_index_keys_to_definition(definition, indexes):
    if indexes:
        for index in indexes:
            _append_attr_definition(definition, index["index_key_name"],
                                    index["index_key_type"])
            if index.get('index_sort_key_name'):
                _append_attr_definition(definition,
                                        index["index_sort_key_name"],
                                        index["index_sort_key_type"])


def _append_attr_definition(definition, attr_name, attr_type):
    """
    :type definition: []
    :type attr_name: str
    :type attr_type: str
    """
    for each in definition:
        if each.AttributeName == attr_name:
            return
    definition.append(dynamodb.AttributeDefinition(
        AttributeName=attr_name,
        AttributeType=attr_type))


def _build_index_definition(index_meta, supplier):
    index_def = supplier(
        IndexName=index_meta['name'],
        KeySchema=[dynamodb.KeySchema(
            AttributeName=index_meta['index_key_name'],
            KeyType='HASH'
        )],
        Projection=dynamodb.Projection(
            ProjectionType='ALL'
        )
    )
    if index_meta.get('index_sort_key_name'):
        index_def.KeySchema.append(dynamodb.KeySchema(
            AttributeName=index_meta['index_sort_key_name'],
            KeyType='RANGE'))
    return index_def


class CfDynamoDbTableConverter(CfResourceConverter):

    def convert(self, name, meta):
        validate_params(name, meta, DYNAMODB_TABLE_REQUIRED_PARAMS)

        read_capacity = meta.get('read_capacity', DEFAULT_READ_CAPACITY)
        write_capacity = meta.get('write_capacity', DEFAULT_WRITE_CAPACITY)
        hash_key_name = meta['hash_key_name']
        hash_key_type = meta['hash_key_type']
        sort_key_name = meta.get('sort_key_name')

        schema = [dynamodb.KeySchema(AttributeName=hash_key_name,
                                     KeyType='HASH')]
        definition = [dynamodb.AttributeDefinition(
            AttributeName=hash_key_name,
            AttributeType=hash_key_type)]
        if sort_key_name:
            sort_key_type = meta['sort_key_type']
            schema.append(dynamodb.KeySchema(AttributeName=sort_key_name,
                                             KeyType='RANGE'))
            definition.append(dynamodb.AttributeDefinition(
                AttributeName=sort_key_name,
                AttributeType=sort_key_type))

        global_indexes = meta.get('global_indexes')
        local_indexes = meta.get('local_indexes')

        _add_index_keys_to_definition(definition=definition,
                                      indexes=global_indexes)
        _add_index_keys_to_definition(definition=definition,
                                      indexes=local_indexes)

        table = dynamodb.Table(dynamodb_table_logic_name(name))
        table.AttributeDefinitions = definition
        table.KeySchema = schema
        table.ProvisionedThroughput = dynamodb.ProvisionedThroughput(
            ReadCapacityUnits=read_capacity,
            WriteCapacityUnits=write_capacity)
        table.TableName = name
        self.template.add_resource(table)

        if global_indexes:
            global_secondary_indexes = []
            for index in global_indexes:
                index_def = _build_index_definition(
                    index_meta=index, supplier=dynamodb.GlobalSecondaryIndex)
                index_def.ProvisionedThroughput = \
                    dynamodb.ProvisionedThroughput(
                        ReadCapacityUnits=read_capacity,
                        WriteCapacityUnits=write_capacity)
                global_secondary_indexes.append(index_def)
            table.GlobalSecondaryIndexes = global_secondary_indexes

        if local_indexes:
            local_secondary_indexes = []
            for index in local_indexes:
                index_def = _build_index_definition(
                    index_meta=index, supplier=dynamodb.LocalSecondaryIndex)
                local_secondary_indexes.append(index_def)
            table.LocalSecondaryIndexes = local_secondary_indexes

        stream_view_type = meta.get('stream_view_type')
        self.configure_table_stream(table=table,
                                    stream_view_type=stream_view_type)

        autoscaling_config = meta.get('autoscaling')
        if autoscaling_config:
            for item in autoscaling_config:
                validate_params(name, item, AUTOSCALING_REQUIRED_PARAMS)
                role_name = item['role_name']
                role_res = self.get_resource(iam_role_logic_name(role_name))
                if role_res:
                    dimension = item['dimension']
                    resource_name = item['resource_name']

                    resource_id = DynamoDBResource.build_res_id(
                        dimension=dimension,
                        resource_name=resource_name,
                        table_name=name)
                    scalable_target = app_scaling.ScalableTarget(
                        to_logic_name(
                            'ApplicationAutoScalingScalableTarget',
                            resource_name))
                    scalable_target.MaxCapacity = str(item['max_capacity'])
                    scalable_target.MinCapacity = str(item['min_capacity'])
                    scalable_target.ResourceId = resource_id
                    scalable_target.RoleARN = role_res.get_att('Arn')
                    scalable_target.ScalableDimension = dimension
                    scalable_target.ServiceNamespace = 'dynamodb'
                    scalable_target.DependsOn = table
                    self.template.add_resource(scalable_target)

                    autoscaling_policy = item.get('config')
                    if autoscaling_policy:
                        policy_name = autoscaling_policy['policy_name']
                        target_value = autoscaling_policy['target_utilization']
                        scale_in_cooldown = \
                            autoscaling_policy.get('scale_in_cooldown')
                        scale_out_cooldown = \
                            autoscaling_policy.get('scale_out_cooldown')
                        metric_type = 'DynamoDBWriteCapacityUtilization' \
                            if 'Write' in dimension \
                            else 'DynamoDBReadCapacityUtilization'

                        scaling_policy = app_scaling.ScalingPolicy(
                            to_logic_name(
                                'ApplicationAutoScalingScalingPolicy',
                                resource_name))
                        scaling_policy.PolicyName = policy_name
                        scaling_policy.PolicyType = 'TargetTrackingScaling'
                        scaling_policy.ResourceId = resource_id
                        scaling_policy.ScalableDimension = dimension
                        scaling_policy.ServiceNamespace = 'dynamodb'
                        scaling_policy.DependsOn = scalable_target

                        metric_spec = app_scaling.PredefinedMetricSpecification(
                            PredefinedMetricType=metric_type)
                        _params = {
                            'PredefinedMetricSpecification': metric_spec,
                            'ScaleInCooldown': scale_in_cooldown,
                            'ScaleOutCooldown': scale_out_cooldown,
                            'TargetValue':target_value
                        }
                        _params = {k: v for k, v in _params.items() if
                                   isinstance(v, (bool, int)) or v}
                        scaling_policy.TargetTrackingScalingPolicyConfiguration = \
                            app_scaling.TargetTrackingScalingPolicyConfiguration(
                                **_params
                            )
                        self.template.add_resource(scaling_policy)
                else:
                    _LOG.warn('Role {} is not found in build meta, '
                              'skipping autoscaling config.'.format(role_name))

    @staticmethod
    def is_stream_enabled(table):
        try:
            stream = table.StreamSpecification
            return True
        except AttributeError:
            return False

    @staticmethod
    def configure_table_stream(table, stream_view_type='NEW_AND_OLD_IMAGES'):
        if stream_view_type:
            table.StreamSpecification = dynamodb.StreamSpecification(
                StreamViewType=stream_view_type)
