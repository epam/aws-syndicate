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
import json

from syndicate.core.resources.cloud_watch_resource import \
    validate_cloud_watch_rule_params
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_helper import deploy_regions

SNS_TARGET = 'sns'
SQS_TARGET = 'sqs'
LAMBDA_TARGET = 'lambda'


class CloudWatchRuleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        validate_cloud_watch_rule_params(name=name, meta=resource)

        rule_type = resource['rule_type']
        regions = deploy_regions(resource_name=name, meta=resource)
        func = RULE_TYPES[rule_type]
        default_region = self.config.region
        for region in regions:
            self.template.add_provider_if_not_exists(region=region)
            tf_resource_name = f'{name}_{region}'
            provider = None
            if region != default_region:
                provider_type = self.template.provider_type()
                provider = f'{provider_type}.{region}'

            func(template=self.template, rule_name=name,
                 resource=resource, resource_name=tf_resource_name,
                 provider=provider)


def event_pattern(event_source, event_names):
    resource = {
        "eventSource": [
            event_source
        ],
        "eventName": event_names
    }
    return resource


def _create_ec2_rule(template, rule_name, resource,
                     resource_name, provider=None):
    instances = resource.get('instances')
    instance_states = resource.get('instance_states')

    event_pattern = {
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"]
    }

    rule_meta = {
        "name": rule_name,
        "event_pattern": event_pattern
    }

    if provider:
        rule_meta['provider'] = provider

    if instances:
        event_pattern["detail"] = {"instance-id": instances}
    if instance_states:
        if event_pattern.get("detail"):
            event_pattern.get("detail").update({"state": instance_states})
        else:
            event_pattern["detail"] = {"state": instance_states}

    rule = {
        resource_name: rule_meta
    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


def _create_schedule_rule(template, rule_name, resource, resource_name,
                          provider=None):
    expression = resource.get('expression')

    rule_meta = {
        "name": rule_name,
        "schedule_expression": expression
    }

    if provider:
        rule_meta['provider'] = provider

    rule = {
        resource_name: rule_meta
    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


def _create_api_call_rule(template, rule_name, resource, resource_name,
                          provider=None):
    operations = resource.get('operations')
    aws_service = resource.get('aws_service')
    custom_pattern = resource.get('custom_pattern')
    if custom_pattern:
        pattern = custom_pattern
    elif aws_service:
        pattern = {
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
            pattern['detail']['eventName'] = operations

    rule_meta = {
        "name": rule_name,
        "event_pattern": json.dumps(pattern)
    }

    if provider:
        rule_meta['provider'] = provider

    rule = {
        resource_name: rule_meta
    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


RULE_TYPES = {
    'schedule': _create_schedule_rule,
    'ec2': _create_ec2_rule,
    'api_call': _create_api_call_rule
}
