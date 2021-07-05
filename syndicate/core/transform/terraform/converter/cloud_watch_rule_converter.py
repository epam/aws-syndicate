import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter

SNS_TARGET = 'sns'
SQS_TARGET = 'sqs'
LAMBDA_TARGET = 'lambda'


class CloudWatchRuleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        rule_type = resource.get('rule_type')
        region = resource.get('region')
        if not region:
            region = self.config.region

        # if rule_type == 'ec2':
        #     instance_ids = resource.get('instance_ids')
        #     instance_states = resource.get('instance_states')
        if rule_type == 'schedule':
            expression = resource.get('expression')
            rule = cloud_watch_event_rule_schedule(rule_name=name,
                                                   cron=expression)
            self.template.add_aws_cloudwatch_event_rule(meta=rule)
        elif rule_type == 'api_call':
            operations = resource.get('operations')
            aws_service = resource.get('aws_service')
            pattern = event_pattern(aws_service, operations)

            rule = cloud_watch_event_rule_api_call(rule_name=name,
                                                   pattern=json.dumps(pattern))
            self.template.add_aws_cloudwatch_event_rule(meta=rule)


def cloud_watch_event_rule_api_call(rule_name, pattern):
    resource = {
        rule_name:
            {
                "name": rule_name,
                "event_pattern": pattern
            }
    }
    return resource


def cloud_watch_event_rule_schedule(rule_name, cron):
    resource = {
        rule_name:
            {
                "name": rule_name,
                "schedule_expression": cron
            }
    }
    return resource


def event_pattern(event_source, event_names):
    resource = {
        "eventSource": [
            event_source
        ],
        "eventName": event_names
    }
    return resource
