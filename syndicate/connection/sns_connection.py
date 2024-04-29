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
import uuid
from json import dumps, loads

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.sns_connection')


@apply_methods_decorator(retry())
class SNSConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('sns', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new SNS connection.')

    def create_topic(self, name):
        """ Crete SNS topic and return topic arn.

        :type name: str
        """
        return self.client.create_topic(Name=name)['TopicArn']

    def subscribe(self, endpoint, topic_name, protocol):
        """
        :param protocol:
            http -- delivery of JSON-encoded message via HTTP POST
            https -- delivery of JSON-encoded message via HTTPS POST
            email -- delivery of message via SMTP
            email-json -- delivery of JSON-encoded message via SMTP
            sms -- delivery of message via SMS
            sqs -- delivery of JSON-encoded message to an Amazon SQS queue
            application -- delivery of JSON-encoded message to an EndpointArn
                           for a mobile app and device.
            lambda -- delivery of JSON message to an AWS Lambda function
        :type protocol: str
        :type topic_name: str
        :param endpoint:
            http protocol, the endpoint is an URL beginning with "http://"
            https protocol, the endpoint is a URL beginning with "https://"
            email protocol, the endpoint is an email address
            email-json protocol, the endpoint is an email address
            sms protocol, the endpoint is a phone number of an SMS-enabled
                device
            sqs protocol, the endpoint is the ARN of an Amazon SQS queue
            application protocol, the endpoint is the EndpointArn of a mobile
                app and device.
            lambda protocol, the endpoint is the ARN of an AWS Lambda function
        :type endpoint: str
        """
        topic_arn = self.get_topic_arn(topic_name)
        if topic_arn is None:
            raise AssertionError(
                'Topic does not exist: {0}.'.format(topic_name))
        self.client.subscribe(TopicArn=topic_arn,
                              Protocol=protocol,
                              Endpoint=endpoint)
        return topic_arn

    def get_topic_arn(self, name):
        """ Get topic arn by name.

        :type name: str
        """
        topics = self.get_topics()
        for each in topics:
            if name == each['TopicArn'].split(':')[-1]:
                return each['TopicArn']

    def get_platform_application(self, name):
        """ Get application arn by name.

        :type name: str
        """
        applications = self.get_platform_applications()
        for each in applications:
            resolved_item = each['PlatformApplicationArn'].split(':')[-1]
            if name == resolved_item.split('/')[-1]:
                return each['PlatformApplicationArn']

    def is_user_subscribed(self, endpoint, topic_name):
        topic_arn = self.get_topic_arn(topic_name)
        subscriptions = self.client.list_subscriptions_by_topic(
            TopicArn=topic_arn)['Subscriptions']
        for each in subscriptions:
            if endpoint == each['Endpoint']:
                return True

    def publish_message(self, topic_name, message):
        topic_arn = self.get_topic_arn(topic_name)
        return self.client.publish(
            TargetArn=topic_arn,
            Message=message,
            MessageAttributes={
                'string': {
                    'DataType': 'String',
                    'StringValue': ' '
                }
            }
        )

    def get_topics(self):
        """ Get all topics."""
        topics = []
        response = self.client.list_topics()
        topics.extend(response.get('Topics'))
        token = response.get('NextToken')
        while token:
            response = self.client.list_topics(NextToken=token)
            topics.extend(response.get('Topics'))
            token = response.get('NextToken')
        return topics

    def get_platform_applications(self):
        """ Get all platform applications."""
        applications = []
        response = self.client.list_platform_applications()
        applications.extend(response.get('PlatformApplications'))
        token = response.get('NextToken')
        while token:
            response = self.client.list_platform_applications(NextToken=token)
            applications.extend(response.get('PlatformApplications'))
            token = response.get('NextToken')
        return applications

    def remove_topic_by_arn(self, topic_arn):
        """ Remove topic by arn.

        :type topic_arn: str
        """
        self.client.delete_topic(TopicArn=topic_arn)

    def remove_topic_by_name(self, topic_name):
        """ Remove topic by arn.

        :type topic_name: str
        """
        arn = self.get_topic_arn(topic_name)
        if arn:
            self.client.delete_topic(TopicArn=arn)

    def set_topic_attribute(self, topic_arn, attr_name, attr_value):
        self.client.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName=attr_name,
            AttributeValue=attr_value
        )

    def allow_service_invoke(self, topic_arn, service):
        existing_attr = self.get_topic_attributes(topic_arn)
        existing_policy = existing_attr['Attributes']['Policy']
        existing_policy_dict = loads(existing_policy)
        policy = {
            "Sid": str(uuid.uuid1()),
            "Effect": "Allow",
            "Principal":
                {
                    "Service": "{0}".format(service)
                },
            "Action": "sns:Publish",
            "Resource": "{0}".format(topic_arn)
        }
        existing_policy_dict['Statement'].append(policy)
        self.set_topic_attribute(topic_arn, 'Policy',
                                 dumps(existing_policy_dict))

    def get_topic_attributes(self, topic_arn):
        return self.client.get_topic_attributes(
            TopicArn=topic_arn
        )

    def get_platform_application_attributes(self, application_arn):
        return self.client.get_platform_application_attributes(
            PlatformApplicationArn=application_arn
        )

    def add_account_permission(self, topic_arn, account_id, action, label):
        if isinstance(account_id, str):
            account_id = [account_id]
        if not isinstance(account_id, list):
            raise AssertionError('Incorrect account id {0}'.format(account_id))

        if isinstance(action, str):
            action = [action]
        if not isinstance(action, list):
            raise AssertionError('Incorrect action {0}'.format(action))

        self.client.add_permission(TopicArn=topic_arn, Label=label,
                                   AWSAccountId=account_id,
                                   ActionName=action)

    def revoke_account_permission(self, topic_arn, label):
        self.client.remove_permission(TopicArn=topic_arn, Label=label)

    def list_subscriptions_by_topic(self, topic_arn):
        subscriptions = []
        try:
            response = self.client.list_subscriptions_by_topic(
                TopicArn=topic_arn)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFound':
                _LOG.warn(f'SNS topic \'{topic_arn}\' is not found')
                return subscriptions
            else:
                raise e
        subscriptions.extend(response.get('Subscriptions'))
        token = response.get('NextToken')
        while token:
            response = self.client.list_subscriptions_by_topic(
                TopicArn=topic_arn, NextToken=token)
            subscriptions.extend(response.get('Subscriptions'))
            token = response.get('NextToken')

        return subscriptions

    def unsubscribe(self, subscription_arn):
        self.client.unsubscribe(SubscriptionArn=subscription_arn)

    def create_platform_endpoint(self, platform_application_arn, token):
        response = self.client.create_platform_endpoint(
            PlatformApplicationArn=platform_application_arn,
            Token=token
        )
        return response.get('EndpointArn')

    def create_platform_application(self, name, platform, attributes):
        response = self.client.create_platform_application(
            Name=name, Platform=platform, Attributes=attributes)
        return response.get('PlatformApplicationArn')

    def remove_application_by_arn(self, application_arn):
        """ Remove application by arn.

        :type application_arn: str
        """
        self.client.delete_platform_application(
            PlatformApplicationArn=application_arn)
