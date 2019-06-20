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
from functools import lru_cache

from syndicate.connection.api_gateway_connection import ApiGatewayConnection
from syndicate.connection.application_autoscaling_connection import (
    ApplicationAutoscaling)
from syndicate.connection.cloud_watch_connection import (EventConnection,
                                                         LogsConnection,
                                                         MetricConnection)
from syndicate.connection.cloudfront_connection import CloudFrontConnection
from syndicate.connection.cognito_identity_connection import (
    CognitoIdentityConnection)
from syndicate.connection.dynamo_connection import DynamoConnection
from syndicate.connection.ec2_connection import EC2Connection
from syndicate.connection.elastic_beanstalk_connection import (
    BeanstalkConnection)
from syndicate.connection.iam_connection import IAMConnection
from syndicate.connection.kinesis_connection import KinesisConnection
from syndicate.connection.kms_connection import KMSConnection
from syndicate.connection.lambda_connection import LambdaConnection
from syndicate.connection.s3_connection import S3Connection
from syndicate.connection.sns_connection import SNSConnection
from syndicate.connection.sqs_connection import SqsConnection
from syndicate.connection.step_functions_connection import SFConnection


class ConnectionProvider(object):
    def __init__(self, credentials):
        self.credentials = credentials.copy()

    @lru_cache(maxsize=None)
    def api_gateway(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return ApiGatewayConnection(**credentials)

    @lru_cache(maxsize=None)
    def lambda_conn(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return LambdaConnection(**credentials)

    @lru_cache(maxsize=None)
    def cw_events(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return EventConnection(**credentials)

    @lru_cache(maxsize=None)
    def dynamodb(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return DynamoConnection(**credentials)

    @lru_cache(maxsize=None)
    def cognito_identity(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return CognitoIdentityConnection(**credentials)

    @lru_cache(maxsize=None)
    def iam(self):
        return IAMConnection(**self.credentials)

    @lru_cache(maxsize=None)
    def s3(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return S3Connection(**credentials)

    @lru_cache(maxsize=None)
    def sns(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return SNSConnection(**credentials)

    @lru_cache(maxsize=None)
    def cw_logs(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return LogsConnection(**credentials)

    @lru_cache(maxsize=None)
    def cw_metric(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return MetricConnection(**credentials)

    @lru_cache(maxsize=None)
    def ec2(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return EC2Connection(**credentials)

    @lru_cache(maxsize=None)
    def cloud_front(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return CloudFrontConnection(**credentials)

    @lru_cache(maxsize=None)
    def beanstalk(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return BeanstalkConnection(**credentials)

    @lru_cache(maxsize=None)
    def step_functions(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return SFConnection(**credentials)

    @lru_cache(maxsize=None)
    def kinesis(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return KinesisConnection(**credentials)

    @lru_cache(maxsize=None)
    def application_autoscaling(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return ApplicationAutoscaling(**credentials)

    @lru_cache(maxsize=None)
    def sqs(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return SqsConnection(**credentials)

    @lru_cache(maxsize=None)
    def kms(self, region=None):
        credentials = self.credentials.copy()
        if region:
            credentials['region'] = region
        return KMSConnection(**credentials)

