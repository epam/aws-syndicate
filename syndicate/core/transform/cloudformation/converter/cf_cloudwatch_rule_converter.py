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
import uuid

from troposphere import events

from syndicate.core.resources.cloud_watch_resource import \
    validate_cloud_watch_rule_params, get_event_bus_arn
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import cloudwatch_rule_logic_name


def _create_schedule_rule(rule_meta, rule_res):
    expression = rule_meta['expression']
    rule_res.ScheduleExpression = expression
    rule_res.Description = rule_res.Name
    rule_res.State = 'ENABLED'


def _create_ec2_rule(rule_meta, rule_res):
    instances = rule_meta.get('instance_ids'),
    instance_states = rule_meta.get('instance_states')
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

    rule_res.EventPattern = event_pattern
    rule_res.Description = rule_res.Name
    rule_res.State = 'ENABLED'


def _create_api_call_rule(rule_meta, rule_res):
    aws_service = rule_meta.get('aws_service')
    operations = rule_meta.get('operations')
    custom_pattern = rule_meta.get('custom_pattern')
    if custom_pattern:
        event_pattern = custom_pattern
    elif aws_service:
        event_pattern = {
            'detail-type': [
                'AWS API Call via CloudTrail'
            ],
            'detail': {
                'eventSource': [
                    '{0}.amazonaws.com'.format(aws_service)
                ]
            }
        }
        if operations:
            event_pattern['detail']['eventName'] = operations
    else:
        raise AssertionError(
            'aws_service or custom_pattern should be specified for rule '
            'with "api_call" type! Resource: {0}'.format(rule_res.Name))
    rule_res.EventPattern = event_pattern
    rule_res.Description = rule_res.Name
    rule_res.State = 'ENABLED'


RULE_TYPES = {
    'schedule': _create_schedule_rule,
    'ec2': _create_ec2_rule,
    'api_call': _create_api_call_rule
}


def attach_rule_target(rule, target_arn, target_id=None):
    if target_id is None:
        target_id = str(uuid.uuid1())
    try:
        targets = rule.Targets
    except AttributeError:
        targets = []
        rule.Targets = targets
    targets.append(events.Target(
        Arn=target_arn,
        Id=target_id)
    )


class CfCloudWatchRuleConverter(CfResourceConverter):

    def convert(self, name, meta):
        validate_cloud_watch_rule_params(name=name, meta=meta)

        rule = events.Rule(cloudwatch_rule_logic_name(name))
        rule.Name = name
        self.template.add_resource(rule)

        rule_type = meta['rule_type']
        func = RULE_TYPES[rule_type]
        func(meta, rule)

        event_buses = meta.get('event_bus_accounts')
        if event_buses:
            self._attach_tenant_rule_targets(rule_res=rule,
                                             event_buses=event_buses)

    def _attach_tenant_rule_targets(self, rule_res, event_buses):
        region = self.config.region
        for event_bus in event_buses:
            target_arn = get_event_bus_arn(event_bus=event_bus,
                                           region=region)
            attach_rule_target(rule=rule_res,
                               target_arn=target_arn)
