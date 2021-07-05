from syndicate.core.resources.lambda_resource import CLOUD_WATCH_RULE_TRIGGER
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.resource_type_mapper import \
    RESOURCE_TYPE_MAPPING


class EventSourceConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        event_sources = resource.get('event_sources')
        if event_sources:
            base_res_type = resource.get('resource_type')
            for event_source in event_sources:
                event_source_res_type = event_source.get('resource_type')
                if event_source_res_type == CLOUD_WATCH_RULE_TRIGGER:
                    target_rule = event_source.get('target_rule')
                    rule_exp = '${aws_cloudwatch_event_rule.' + target_rule + '.name}'

                    tf_resource_type = RESOURCE_TYPE_MAPPING.get(base_res_type)
                    resource_arn = '${' + tf_resource_type + '.' + name + '.arn}'

                    trigger = cloud_watch_trigger(resource_type=name,
                                                  rule_name=rule_exp,
                                                  resource_arn=resource_arn)
                    self.template.add_aws_cloudwatch_event_target(trigger)
                # elif event_source_res_type == DYNAMO_DB_TRIGGER:
                # elif event_source_res_type == S3_TRIGGER:
                # elif event_source_res_type == SNS_TOPIC_TRIGGER:
                # elif event_source_res_type == KINESIS_TRIGGER:
                # elif event_source_res_type == SQS_TRIGGER:


def cloud_watch_trigger(resource_type, resource_arn, rule_name):
    resource = {
        resource_type:
            {
                "arn": resource_arn,
                "rule": rule_name
            }
    }
    return resource
