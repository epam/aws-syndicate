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
import boto3

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.application_autoscaling_connection')


@apply_methods_decorator(retry())
class ApplicationAutoscaling(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = boto3.client('application-autoscaling', region,
                                   aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key,
                                   aws_session_token=aws_session_token)
        _LOG.debug('Opened new Application autoscaling connection.')

    def register_target(self, service_namespace, resource_id,
                        scalable_dimension, min_capacity=None,
                        max_capacity=None, role_arn=None):
        params = dict(ServiceNamespace=service_namespace,
                      ResourceId=resource_id,
                      ScalableDimension=scalable_dimension)
        if min_capacity:
            params['MinCapacity'] = int(min_capacity)
        if max_capacity:
            params['MaxCapacity'] = int(max_capacity)
        if role_arn:
            params['RoleARN'] = role_arn
        self.client.register_scalable_target(**params)

    def put_step_scaling_policy(self, policy_name, service_namespace,
                                resource_id,
                                scalable_dimension,
                                adjustment_type=None,
                                metric_interval_lower_bound=None,
                                metric_interval_upper_bound=None,
                                scaling_adjustment=None,
                                min_adjustment_magnitude=None,
                                cooldown=None,
                                metric_aggregation_type=None):
        params = dict(PolicyName=policy_name,
                      ServiceNamespace=service_namespace,
                      ResourceId=resource_id,
                      ScalableDimension=scalable_dimension,
                      PolicyType='StepScaling')
        step_scaling_config_dict = dict()
        if adjustment_type:
            step_scaling_config_dict['AdjustmentType'] = adjustment_type
        if min_adjustment_magnitude:
            step_scaling_config_dict[
                'MinAdjustmentMagnitude'] = min_adjustment_magnitude
        if cooldown:
            step_scaling_config_dict['Cooldown'] = cooldown
        if metric_aggregation_type:
            step_scaling_config_dict[
                'MetricAggregationType'] = metric_aggregation_type
        step_adjustment_dict = dict()
        if metric_interval_lower_bound:
            step_adjustment_dict[
                'MetricIntervalLowerBound'] = metric_interval_lower_bound
        if metric_interval_upper_bound:
            step_adjustment_dict[
                'MetricIntervalUpperBound'] = metric_interval_upper_bound
        if scaling_adjustment:
            step_adjustment_dict['ScalingAdjustment'] = scaling_adjustment
        if step_adjustment_dict:
            step_scaling_config_dict['StepAdjustments'] = step_adjustment_dict
        if step_scaling_config_dict:
            params['StepScalingPolicyConfiguration'] = step_scaling_config_dict
        return self.client.put_scaling_policy(**params)

    def put_target_scaling_policy(self, policy_name, service_namespace,
                                  resource_id, scalable_dimension,
                                  target_value=None,
                                  predefined_metric_type=None,
                                  resource_label=None, metric_name=None,
                                  namespace=None, dimensions=None,
                                  statistic=None, unit=None,
                                  scale_out_cooldown=None,
                                  scale_in_cooldown=None):
        params = dict(PolicyName=policy_name,
                      ServiceNamespace=service_namespace,
                      ResourceId=resource_id,
                      ScalableDimension=scalable_dimension,
                      PolicyType='TargetTrackingScaling')
        target_scaling_config_dict = dict()
        if target_value:
            target_scaling_config_dict['TargetValue'] = target_value
        predefined_config_dict = dict()
        if predefined_metric_type:
            predefined_config_dict[
                'PredefinedMetricType'] = predefined_metric_type
        if resource_label:
            predefined_config_dict['ResourceLabel'] = resource_label
        if predefined_config_dict:
            target_scaling_config_dict[
                'PredefinedMetricSpecification'] = predefined_config_dict
        customized_config_dict = dict()
        if metric_name:
            customized_config_dict['MetricName'] = metric_name
        if namespace:
            customized_config_dict['Namespace'] = namespace
        if dimensions:
            customized_config_dict['Dimensions'] = dimensions
        if statistic:
            customized_config_dict['Statistic'] = statistic
        if unit:
            customized_config_dict['Unit'] = unit
        if customized_config_dict:
            params['CustomizedMetricSpecification'] = customized_config_dict
        if scale_out_cooldown:
            target_scaling_config_dict['ScaleOutCooldown'] = scale_out_cooldown
        if scale_in_cooldown:
            target_scaling_config_dict['ScaleInCooldown'] = scale_in_cooldown
        if target_scaling_config_dict:
            params[
                'TargetTrackingScalingPolicyConfiguration'] = target_scaling_config_dict
        return self.client.put_scaling_policy(**params)

    def deregister_scalable_target(self, service_namespace, resource_id,
                                   scalable_dimension):
        params = dict(ResourceId=resource_id,
                      ScalableDimension=scalable_dimension,
                      ServiceNamespace=service_namespace)
        return self.client.deregister_scalable_target(**params)

    def describe_scalable_targets(self, service_namespace, resources_ids=None,
                                  scalable_dimension=None):
        params = dict(ServiceNamespace=service_namespace)
        if resources_ids:
            params['ResourceIds'] = resources_ids
        if scalable_dimension:
            params['ScalableDimension'] = scalable_dimension
        targets = []
        response = self.client.describe_scalable_targets(**params)
        token = response.get('NextToken')
        targets.extend(response.get('ScalableTargets'))
        while token:
            params['NextToken'] = token
            response = self.client.describe_scalable_targets(**params)
            token = response.get('NextToken')
            targets.extend(response.get('ScalableTargets'))
        return targets

    def describe_scaling_policies(self, service_namespace, policy_names,
                                  resource_id=None, scalable_dimension=None):
        params = dict(ServiceNamespace=service_namespace)
        if policy_names:
            params['PolicyNames'] = policy_names
        if scalable_dimension:
            params['ScalableDimension'] = scalable_dimension
        if resource_id:
            params['ResourceId'] = resource_id
        targets = []
        response = self.client.describe_scaling_policies(**params)
        token = response.get('NextToken')
        targets.extend(response.get('ScalingPolicies'))
        while token:
            params['NextToken'] = token
            response = self.client.describe_scaling_policies(**params)
            token = response.get('NextToken')
            targets.extend(response.get('ScalingPolicies'))
        return targets
