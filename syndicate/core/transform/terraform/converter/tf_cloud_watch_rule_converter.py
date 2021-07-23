import json

from syndicate.core.resources.cloud_watch_resource import \
    validate_cloud_watch_rule_params
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter

SNS_TARGET = 'sns'
SQS_TARGET = 'sqs'
LAMBDA_TARGET = 'lambda'


class CloudWatchRuleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        validate_cloud_watch_rule_params(name=name, meta=resource)

        rule_type = resource['rule_type']
        func = RULE_TYPES[rule_type]
        func(template=self.template, rule_name=name, resource=resource)


def event_pattern(event_source, event_names):
    resource = {
        "eventSource": [
            event_source
        ],
        "eventName": event_names
    }
    return resource


def _create_ec2_rule(template, rule_name, resource):
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

    if instances:
        event_pattern["detail"] = {"instance-id": instances}
    if instance_states:
        if event_pattern.get("detail"):
            event_pattern.get("detail").update({"state": instance_states})
        else:
            event_pattern["detail"] = {"state": instance_states}

    rule = {
        rule_name: rule_meta
    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


def _create_schedule_rule(template, rule_name, resource):
    expression = resource.get('expression')

    rule_meta = {
        "name": rule_name,
        "schedule_expression": expression
    }

    rule = {
        rule_name: rule_meta

    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


def _create_api_call_rule(template, rule_name, resource):
    operations = resource.get('operations')
    aws_service = resource.get('aws_service')
    pattern = event_pattern(aws_service, operations)

    rule_meta = {
        "name": rule_name,
        "event_pattern": json.dumps(pattern)
    }

    rule = {
        rule_name: rule_meta
    }
    template.add_aws_cloudwatch_event_rule(meta=rule)


RULE_TYPES = {
    'schedule': _create_schedule_rule,
    'ec2': _create_ec2_rule,
    'api_call': _create_api_call_rule
}
