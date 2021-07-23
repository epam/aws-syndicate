import json
import uuid

from syndicate.core.resources.lambda_resource import CLOUD_WATCH_RULE_TRIGGER
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_helper import deploy_regions
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_cloud_watch_event_rule_name_ref, build_sns_topic_arn_ref


class SNSTopicConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        regions = deploy_regions(resource_name=name, meta=resource)
        if len(regions) == 1 and regions[0] == self.config.region:
            region = self.config.region
            self.create_sns_topic_in_region(region=region,
                                            name=name, resource=resource)
        else:
            for region in regions:
                self.template.add_provider_if_not_exists(region=region)
                provider_type = self.template.provider_name()
                provider = f'{provider_type}.{region}'

                self.create_sns_topic_in_region(name=name, resource=resource,
                                                provider=provider,
                                                region=region)

    def create_sns_topic_in_region(self, name, resource, region,
                                   provider=None):
        tf_resource_name = f'{name}_{region}'
        topic = sns_topic(topic_resource_name=tf_resource_name,
                          sns_topic_name=name, provider=provider)
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
                    self._allow_service_invoke(topic=topic_name)

    def _allow_service_invoke(self, topic):
        topic_policy_document = sns_topic_policy_document(topic=topic)
        document_json = json.dumps(topic_policy_document)
        topic_policy = sns_topic_policy(policy_json=document_json, topic=topic)
        self.template.add_aws_sns_topic_policy(meta=topic_policy)


def cloud_watch_trigger(topic_name, topic_arn, rule_name):
    resource = {
        build_terraform_resource_name(topic_name, 'trigger'):
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


def sns_topic_policy(policy_json, topic, provider=None):
    topic_policy_resource_name = build_terraform_resource_name(topic, 'policy')

    policy_meta = {
        "arn": build_sns_topic_arn_ref(sns_topic=topic),
        "policy": policy_json
    }
    if provider:
        policy_meta['provider'] = provider
    resource = {
        topic_policy_resource_name: policy_meta
    }
    return resource


def sns_topic(topic_resource_name, sns_topic_name, provider=None):
    topic = {
        "name": sns_topic_name
    }
    if provider:
        topic['provider'] = provider
    resource = {
        topic_resource_name: topic
    }
    return resource
