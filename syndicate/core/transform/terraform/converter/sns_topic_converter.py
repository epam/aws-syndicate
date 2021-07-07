import json
import uuid

from syndicate.core.resources.lambda_resource import CLOUD_WATCH_RULE_TRIGGER
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_sns_topic_arn_ref, build_cloud_watch_event_rule_name_ref
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class SNSTopicConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        topic = sns_topic(sns_topic_name=name)
        self.template.add_aws_sns_topic(meta=topic)
        self.process_event_sources(resource=resource, topic_name=name)

    def process_event_sources(self, resource, topic_name):
        event_sources = resource.get('event_sources')
        if event_sources:
            for event_source in event_sources:
                event_source_res_type = event_source.get('resource_type')
                if event_source_res_type == CLOUD_WATCH_RULE_TRIGGER:
                    target_rule = event_source.get('target_rule')
                    rule_exp = build_cloud_watch_event_rule_name_ref(
                        target_rule=target_rule)

                    sns_topic_arn = build_sns_topic_arn_ref(
                        sns_topic=topic_name)

                    trigger = cloud_watch_trigger(topic_name=topic_name,
                                                  rule_name=rule_exp,
                                                  topic_arn=sns_topic_arn)
                    self.template.add_aws_cloudwatch_event_target(trigger)
                    self.allow_service_invoke(topic=topic_name)

    def allow_service_invoke(self, topic):
        topic_policy_document = sns_topic_policy_document(topic=topic)
        document_json = json.dumps(topic_policy_document)
        topic_policy = sns_topic_policy(policy_json=document_json, topic=topic)
        self.template.add_aws_sns_topic_policy(meta=topic_policy)


def cloud_watch_trigger(topic_name, topic_arn, rule_name):
    resource = {
        f'{topic_name}_trigger':
            {
                "arn": topic_arn,
                "rule": rule_name
            }
    }
    return resource


def sns_topic_policy_document(topic):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": str(uuid.uuid1()),
                "Effect": "Allow",
                "Principal":
                    {
                        "Service": 'events.amazonaws.com'
                    },
                "Action": "sns:Publish",
                "Resource": build_sns_topic_arn_ref(sns_topic=topic)
            }
        ]
    }
    return policy_document


def sns_topic_policy(policy_json, topic):
    resource = {
        f'{topic}_policy': [
            {
                "arn": build_sns_topic_arn_ref(sns_topic=topic),
                "policy": policy_json
            }
        ]
    }
    return resource


def sns_topic(sns_topic_name):
    resource = {
        sns_topic_name: [
            {
                "name": sns_topic_name
            }
        ]
    }
    return resource
