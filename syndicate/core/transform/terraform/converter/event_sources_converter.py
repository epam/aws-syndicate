import uuid

from syndicate.core.transform.terraform.tf_transform_helper import \
    build_cloud_watch_event_rule_name_ref, build_resource_arn_ref
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
                    rule_exp = build_cloud_watch_event_rule_name_ref(
                        target_rule=target_rule)

                    tf_resource_type = RESOURCE_TYPE_MAPPING.get(base_res_type)
                    resource_arn = build_resource_arn_ref(
                        tf_resource_type=tf_resource_type, name=name)

                    trigger = cloud_watch_trigger(resource_type=name,
                                                  rule_name=rule_exp,
                                                  resource_arn=resource_arn)
                    self.template.add_aws_cloudwatch_event_target(trigger)
                # elif event_source_res_type == SNS_TOPIC_TRIGGER:
                # elif event_source_res_type == DYNAMO_DB_TRIGGER:
                # elif event_source_res_type == S3_TRIGGER:

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


# def allow_service_invoke(topic, service):
#     policy_document = {
#         "Version": "2012-10-17",
#         "Statement": [
#             {
#                 "Sid": str(uuid.uuid1()),
#                 "Effect": "Allow",
#                 "Principal":
#                     {
#                         "Service": service
#                     },
#                 "Action": "sns:Publish",
#                 "Resource": build_sns_topic_arn_ref(sns_topic=topic)
#             }
#         ]
#     }
#
#
# def sns_topic_policy(res_name, policy_json, topic):
#     resource = {
#         res_name: [
#             {
#                 "arn": build_sns_topic_arn_ref(sns_topic=topic),
#                 "policy": policy_json
#             }
#         ]
#     }
#     return resource
