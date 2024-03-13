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

from troposphere import sns, Template

from syndicate.core.resources.helper import validate_params
from syndicate.core.resources.sns_resource import \
    SNS_CLOUDWATCH_TRIGGER_REQUIRED_PARAMS
from .cf_cloudwatch_rule_converter import attach_rule_target
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import (to_logic_name, sns_topic_logic_name,
                                  cloudwatch_rule_logic_name)


class CfSnsConverter(CfResourceConverter):

    def __init__(self, template: Template, config=None,
                 resources_provider=None):
        super().__init__(template, config, resources_provider)
        self.create_trigger = {
            'cloudwatch_rule_trigger':
                self._create_cloud_watch_trigger_from_meta,
            'eventbridge_rule_trigger':
                self._create_cloud_watch_trigger_from_meta
        }

    def convert(self, name, meta):
        topic = sns.Topic(sns_topic_logic_name(name))
        topic.TopicName = name
        topic.Subscription = []
        self.template.add_resource(topic)
        # region = meta.get('region') TODO: process region param

        event_sources = meta.get('event_sources')
        if event_sources:
            for trigger_meta in event_sources:
                trigger_type = trigger_meta['resource_type']
                func = self.create_trigger[trigger_type]
                func(topic, trigger_meta)

    def _create_cloud_watch_trigger_from_meta(self, topic, trigger_meta):
        required_parameters = SNS_CLOUDWATCH_TRIGGER_REQUIRED_PARAMS
        validate_params(topic.TopicName, trigger_meta, required_parameters)
        rule_name = trigger_meta['target_rule']
        rule = self.get_resource(cloudwatch_rule_logic_name(rule_name))
        attach_rule_target(rule=rule,
                           target_arn=topic.ref())
        topic_policy = self.allow_service_invoke_policy(
            topic=topic,
            service='events.amazonaws.com')
        self.template.add_resource(topic_policy)

    @staticmethod
    def allow_service_invoke_policy(topic, service):
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": str(uuid.uuid1()),
                    "Effect": "Allow",
                    "Principal":
                        {
                            "Service": service
                        },
                    "Action": "sns:Publish",
                    "Resource": topic.ref()
                }
            ]
        }
        topic_policy = sns.TopicPolicy(
            to_logic_name('SNSTopicPolicy', topic.title))
        topic_policy.Topics = [topic.ref()]
        topic_policy.PolicyDocument = policy_document
        return topic_policy

    @staticmethod
    def subscribe(topic, protocol, endpoint):
        subscriptions = topic.Subscription
        subscriptions.append(sns.Subscription(
            Protocol=protocol,
            Endpoint=endpoint
        ))
