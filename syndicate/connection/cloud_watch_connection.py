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
import json
import uuid
from json import dumps
from typing import Optional

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.constants import (
    POSSIBLE_RETENTION_DAYS, DEFAULT_LOGS_EXPIRATION
)

_LOG = get_logger('syndicate.connection.cloud_watch_connection')


def get_lambda_log_group_name(lambda_name):
    return '/aws/lambda/' + lambda_name


@apply_methods_decorator(retry())
class LogsConnection(object):
    """ CloudWatch Log connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('logs', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Cloudwatch logs connection.')

    def delete_log_group_name(self, name):
        """ Delete all existing logs.
        :type name: str
        """
        self.client.delete_log_group(logGroupName=name)

    def create_subscription(self, log_group_name, filter_name, lambda_arn,
                            filter_pattern=''):
        """ Subscribes provided lambda to the provided log group.

        :type log_group_name: str
        :type filter_name: str
        :type lambda_arn: str
        :type filter_pattern: str
        """
        log_group_name = get_lambda_log_group_name(log_group_name)
        self.client.put_subscription_filter(logGroupName=log_group_name,
                                            filterName=filter_name,
                                            filterPattern=filter_pattern,
                                            destinationArn=lambda_arn)

    def create_log_group_with_retention_days(self, group_name: str,
                                             retention_in_days: int):
        """ Creates a log group for provided lambda function and sets
        the retention .

        :type group_name: str
        :type retention_in_days: int
        """

        if retention_in_days == 0:
            retention_in_days = POSSIBLE_RETENTION_DAYS[-1]
        if retention_in_days not in POSSIBLE_RETENTION_DAYS:
            _LOG.warning(
                f"Invalid value for 'logs_expiration': {retention_in_days}. "
                f"Possible values: {', '.join(map(str, POSSIBLE_RETENTION_DAYS))}"
                f" or 0 for max limit. Set default {DEFAULT_LOGS_EXPIRATION}"
            )
            retention_in_days = DEFAULT_LOGS_EXPIRATION

        log_group_name = get_lambda_log_group_name(group_name)
        self.client.create_log_group(logGroupName=log_group_name)
        self.client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_in_days
        )

    def update_log_group_retention_days(self, group_name: str,
                                        retention_in_days: int):
        """ Updates the retention of a log group for provided lambda function.

        :type group_name: str
        :type retention_in_days: int
        """

        if retention_in_days == 0:
            retention_in_days = POSSIBLE_RETENTION_DAYS[-1]
        if retention_in_days not in POSSIBLE_RETENTION_DAYS:
            _LOG.warning(
                f"Invalid value for 'logs_expiration': {retention_in_days}. "
                f"Possible values: {', '.join(map(str, POSSIBLE_RETENTION_DAYS))}"
                f" or 0 for max limit. Set default {DEFAULT_LOGS_EXPIRATION}"
            )
            retention_in_days = DEFAULT_LOGS_EXPIRATION
        log_group_name = get_lambda_log_group_name(group_name)
        try:
            res = self.client.describe_log_groups(
                logGroupNamePrefix=log_group_name)
        except Exception as e:
            _LOG.warning(f"Error on describing log group: {log_group_name}. "
                         f"Error: {str(e)}")
            return
        if not res.get('logGroups'):
            _LOG.warning(f"Log group does not exist: {log_group_name}.")
            return
        self.client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_in_days
        )
        _LOG.info(
            f"Successfully updated the cloudWatch log group: {log_group_name}")

    def get_log_group_arns(self):
        """ Returns ARNs for each log group that currently exists. """
        response = self.get_all_log_groups()
        return [each['arn'] for each in response]

    def get_log_group_names(self):
        """ Get all log group names from CloudWatch Log."""
        response = self.get_all_log_groups()
        return [each['logGroupName'] for each in response]

    def get_all_log_groups(self):
        groups = []
        response = self.client.describe_log_groups()
        groups.extend(response.get('logGroups'))
        token = response.get('nextToken')
        while token:
            response = self.client.describe_log_groups(nextToken=token)
            groups.extend(response.get('logGroups'))
            token = response.get('nextToken')
        return groups


@apply_methods_decorator(retry())
class EventConnection(object):
    """ CloudWatch Event connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('events', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Cloudwatch events connection.')

    def create_schedule_rule(self, name, expression, state='ENABLED'):
        """ Create CloudWatch schedule rule for resource invocation.

        :type name: str
        :type expression: str
        :param expression: e.g. rate(1 hour)
        :type state: str
        :param state: 'ENABLED'/'DISABLED'
        """
        self.client.put_rule(Name=name, ScheduleExpression=expression,
                             State=state, Description=name)

    def create_ec2_rule(self, name, instances=None, instance_states=None,
                        state='ENABLED'):
        """ Create CloudWatch ec2 rule for resource invocation.

        :type name: str
        :type instances: list
        :type instance_states: list
        :type state: str
        """
        event_pattern = {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Instance State-change Notification"]
        }
        if instances:
            event_pattern["detail"] = {"instance-id": instances}
        if instance_states:
            if event_pattern.get("detail"):
                event_pattern.get("detail").update({"state": instance_states})
            else:
                event_pattern["detail"] = {"state": instance_states}

        self.client.put_rule(Name=name, EventPattern=dumps(event_pattern),
                             State=state, Description=name)

    def create_api_call_rule(self, name, aws_service=None, operations=None,
                             custom_pattern=None, state='ENABLED'):
        """ To select ANY operation do not set 'operations' param.

        :type aws_service:
        :param aws_service: e.g. 'ec2'
        :type name: str
        :type operations: list
        :type custom_pattern: dict
        :param operations:
        :type state: str
        """
        if custom_pattern:
            event_pattern = custom_pattern
        elif aws_service:
            event_pattern = {
                "detail-type":
                    [
                        "AWS API Call via CloudTrail"
                    ],
                "detail":
                    {
                        "eventSource":
                            [
                                "{0}.amazonaws.com".format(aws_service)
                            ]
                    }
            }
            if operations:
                event_pattern['detail']['eventName'] = operations
        else:
            raise AssertionError(
                f'aws_service or custom_pattern should be specified for rule '
                f'with "api_call" type! Resource: {name}')

        self.client.put_rule(Name=name, EventPattern=dumps(event_pattern),
                             State=state, Description=name)

    def get_rule(self, rule_name):
        try:
            return self.client.describe_rule(Name=rule_name)
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_rule_arn(self, name):
        rule = self.get_rule(name)
        if rule:
            return rule['Arn']

    def add_rule_target(self, rule_name: str, target_arn: str,
                        input_: Optional[dict] = None):
        """Add to CloudWatch rule targets for invocations
        :type rule_name: str
        :type target_arn: str
        :type input_: Optional[dict]
        """
        target = {'Id': str(uuid.uuid1()), 'Arn': target_arn}
        if input_ and isinstance(input_, dict):
            target['Input'] = json.dumps(input_)
        self.client.put_targets(Rule=rule_name, Targets=[target, ])

    def add_rule_sf_target(self, rule_name, target_arn, input, role_arn):
        """ Add to CloudWatch rule targets for invocations.

        :type rule_name: str
        :type target_arn: str
        """
        self.client.put_targets(Rule=rule_name,
                                Targets=[{
                                    'Id': str(uuid.uuid1()),
                                    'Arn': target_arn,
                                    'Input': json.dumps(input),
                                    'RoleArn': role_arn
                                }])

    def list_targets(self, rule_name):
        """ Lists the targets assigned to the specified rule.

        :type rule_name: str
        """
        return self.client.list_targets_by_rule(Rule=rule_name)

    def list_rules(self):
        """ Get list of rules for region."""
        rules = []
        response = self.client.list_rules()
        rules.extend(response.get('Rules'))
        token = response.get('NextToken')
        while token:
            response = self.client.list_rules(NextToken=token)
            rules.extend(response.get('Rules'))
            token = response.get('NextToken')
        return rules

    def clear_rules(self):
        """ Clear all rules that exist in region."""
        rules = self.list_rules()
        if rules:
            for rule in rules:
                self.remove_rule(rule['Name'])

    def remove_rule(self, rule_name):
        """ Remove single rule by name with targets.

        :type rule_name: str
        """
        response = self.client.list_targets_by_rule(Rule=rule_name)
        if response['Targets']:
            targets = response['Targets']
            target_ids = [target['Id'] for target in targets]
            self.client.remove_targets(Rule=rule_name, Ids=target_ids)
        self.client.delete_rule(Name=rule_name)

    def list_targets_by_rule(self, rule_name):
        targets = []
        response = self.client.list_targets_by_rule(Rule=rule_name)
        targets.extend(response.get('Targets'))
        token = response.get('NextToken')
        while token:
            response = self.client.list_targets_by_rule(Rule=rule_name,
                                                        NextToken=token)
            targets.extend(response.get('Targets'))
            token = response.get('NextToken')
        return targets

    def remove_targets(self, rule_name, target_ids):
        self.client.remove_targets(Rule=rule_name, Ids=target_ids)

    def describe_event_bus(self):
        return self.client.describe_event_bus()

    def add_event_bus_permissions(self, account_id, action='events:PutEvents'):
        """ Permits the specified AWS account to put events to current
        account's default event bus.
        http://boto3.readthedocs.io/en/latest/reference/services/events.html#CloudWatchEvents.Client.put_permission
        :type account_id: str
        :param action: Currently, this must be 'events:PutEvents'
        :type action: str
        """
        event_bus = self.describe_event_bus()
        statement_id = _find_statement_id_in_event_bus_policy(account_id,
                                                              event_bus)
        if not statement_id:
            self.client.put_permission(Action=action, Principal=account_id,
                                       StatementId=str(uuid.uuid1()))

    def remove_event_bus_permissions(self, account_id):
        """Revokes the permission of another AWS account to be able to put
        events to current account's default event bus.

        :type account_id: str
        """
        event_bus = self.describe_event_bus()
        statement_id = _find_statement_id_in_event_bus_policy(account_id,
                                                              event_bus)
        if statement_id:
            self.client.remove_permission(StatementId=statement_id)


def _find_statement_id_in_event_bus_policy(account_id, event_bus):
    if event_bus and event_bus.get('Policy'):
        policy = json.loads(event_bus.get('Policy'))
        for statement in policy.get('Statement'):
            principal = statement['Principal']
            if isinstance(principal, str):
                if account_id == principal:
                    return statement['Sid']
            else:
                if account_id in principal['AWS']:
                    return statement['Sid']


@apply_methods_decorator(retry())
class MetricConnection(object):
    """ CloudWatch Log connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('cloudwatch', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Cloudwatch metric connection.')

    def put_metric_data(self, name_space, metric_name, value, dimensions=None,
                        timestamp=None, statistic_values=None, unit=None):
        """
        :param value: metric value
        :type name_space: str
        :type metric_name: str
        :type dimensions: list of dicts
        :param dimensions: [ { 'Name': 'string', 'Value': 'string' } ]
        :type timestamp: datetime
        :type statistic_values: dict
        :param statistic_values: { 'SampleCount': 123.0, 'Sum': 123.0,
                                   'Minimum': 123.0, 'Maximum': 123.0 }
        :type unit: str
        :param unit: 'Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|
        'Kilobytes'|'Megabytes'|'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|
        'Megabits'|'Gigabits'|'Terabits'|'Percent'|'Count'|'Bytes/Second'|
        'Kilobytes/Second'|'Megabytes/Second'|'Gigabytes/Second'|
        'Terabytes/Second'|'Bits/Second'|'Kilobits/Second'|'Megabits/Second'|
        'Gigabits/Second'|'Terabits/Second'|'Count/Second'|'None'
        """
        metric_data = {
            'MetricName': metric_name,
            'Value': value
        }
        if dimensions:
            metric_data['Dimensions'] = dimensions
        if statistic_values:
            metric_data['StatisticValues'] = statistic_values
        if unit:
            metric_data['Unit'] = unit
        if timestamp:
            metric_data['Timestamp'] = timestamp

        self.client.put_metric_data(Namespace=name_space,
                                    MetricData=[metric_data])

    def put_metric_alarm(self, alarm_name, metric_name, namespace, period,
                         evaluation_periods, threshold, comparison_operator,
                         statistic, actions_enabled=None, ok_actions=None,
                         alarm_actions=None, insufficient_data_actions=None,
                         extended_statistic=None, dimensions=None, unit=None,
                         description=None, datapoints=None,
                         evaluate_low_sample_count_percentile=None):
        """
        :type alarm_name: str
        :type metric_name: str
        :type namespace: str
        :type period: int
        :type evaluation_periods: int
        :type threshold: float
        :type comparison_operator: str
        :param comparison_operator: 'GreaterThanOrEqualToThreshold'|
        'GreaterThanThreshold'|'LessThanThreshold'|'LessThanOrEqualToThreshold'
        :type actions_enabled: bool
        :type ok_actions: list of strings
        :type alarm_actions: list of strings
        :type insufficient_data_actions: list of strings
        :type statistic: str
        :param statistic: 'SampleCount'|'Average'|'Sum'|'Minimum'|'Maximum'
        :type extended_statistic: str
        :type dimensions: list of dicts
        :param dimensions: [{ 'Name': 'string', 'Value': 'string' },]
        :type unit: str
        :param unit: 'Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|
        'Kilobytes'|'Megabytes'|'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|
        'Megabits'|'Gigabits'|'Terabits'|'Percent'|'Count'|'Bytes/Second'|
        'Kilobytes/Second'|'Megabytes/Second'|'Gigabytes/Second'|
        'Terabytes/Second'|'Bits/Second'|'Kilobits/Second'|'Megabits/Second'|
        'Gigabits/Second'|'Terabits/Second'|'Count/Second'|'None'
        :type description: str
        :param description: the description for the alarm
        :type datapoints: int
        :param datapoints: number of datapoints that must be breaching to
        trigger the alarm
        :type evaluate_low_sample_count_percentile: str
        :param evaluate_low_sample_count_percentile: 'evaluate'|'ignore'
        """
        params = dict(AlarmName=alarm_name, MetricName=metric_name,
                      Namespace=namespace, Period=period, Threshold=threshold,
                      EvaluationPeriods=evaluation_periods,
                      ComparisonOperator=comparison_operator,
                      Statistic=statistic)
        if actions_enabled:
            params['ActionsEnabled'] = actions_enabled
        if ok_actions:
            params['OKActions'] = ok_actions
        if alarm_actions:
            params['AlarmActions'] = alarm_actions
        if insufficient_data_actions:
            params['InsufficientDataActions'] = insufficient_data_actions
        if extended_statistic:
            params['ExtendedStatistic'] = extended_statistic
        if unit:
            params['Unit'] = unit
        if dimensions:
            params['Dimensions'] = dimensions
        if description:
            params['AlarmDescription'] = description
        if evaluate_low_sample_count_percentile:
            params['EvaluateLowSampleCountPercentile'] = \
                evaluate_low_sample_count_percentile
        if datapoints:
            params['DatapointsToAlarm'] = datapoints
        self.client.put_metric_alarm(**params)

    def remove_alarms(self, alarm_names):
        """
        :type alarm_names: str or list
        """
        if isinstance(alarm_names, str):
            alarm_names = [alarm_names]
        self.client.delete_alarms(AlarmNames=alarm_names)

    def alarm_list(self, alarm_names):
        """
        :type alarm_names: str or list
        """
        if isinstance(alarm_names, str):
            alarm_names = [alarm_names]
        alarms = []
        response = self.client.describe_alarms(AlarmNames=alarm_names)
        token = response.get('NextToken')
        alarms.extend(response.get('MetricAlarms'))
        while token:
            response = self.client.describe_alarms(AlarmNames=alarm_names,
                                                   NextToken=token)
            token = response.get('NextToken')
            alarms.extend(response.get('MetricAlarms'))
        return alarms

    def all_alarms(self):
        alarms = []
        response = self.client.describe_alarms()
        token = response.get('NextToken')
        alarms.extend(response.get('MetricAlarms'))
        while token:
            response = self.client.describe_alarms(NextToken=token)
            token = response.get('NextToken')
            alarms.extend(response.get('MetricAlarms'))
        return alarms

    def is_alarm_exists(self, alarm_names):
        """
        :type alarm_names: str or list
        """
        if isinstance(alarm_names, str):
            alarm_names = [alarm_names]
        alarms = self.alarm_list(alarm_names)
        existing_names = [each['AlarmName'] for each in alarms]
        for alarm_name in alarm_names:
            if alarm_name not in existing_names:
                return False
        return True

    def list_metrics(self, name=None, namespace=None, dimensions=None):
        params = dict()
        if name:
            params['MetricName'] = name
        if namespace:
            params['Namespace'] = namespace
        if dimensions:
            params['Dimensions'] = dimensions
        metrics = []
        response = self.client.list_metrics(**params)
        metrics.extend(response.get('Metrics', []))
        token = response.get('NextToken')
        while token:
            params['NextToken'] = token
            response = self.client.list_metrics(**params)
            metrics.extend(response.get('Metrics', []))
            token = response.get('NextToken')
        return metrics

    def describe_alarms(self, alarm_names=None, alarm_name_prefix=None,
                        state_value=None,
                        action_prefix=None):
        params = dict()
        if alarm_names:
            params['AlarmNames'] = alarm_names
        if alarm_name_prefix:
            params['AlarmNamePrefix'] = alarm_name_prefix
        if state_value:
            params['StateValue'] = state_value
        if action_prefix:
            params['ActionPrefix'] = action_prefix
        alarms = []
        response = self.client.describe_alarms(**params)
        alarms.extend(response.get('MetricAlarms', []))
        token = response.get('NextToken')
        while token:
            params['NextToken'] = token
            response = self.client.describe_alarms(**params)
            alarms.extend(response.get('MetricAlarms', []))
            token = response.get('NextToken')
        return alarms
