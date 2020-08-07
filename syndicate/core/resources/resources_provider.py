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
from syndicate.connection import ConnectionProvider
from syndicate.core.resources.api_gateway_resource import ApiGatewayResource
from syndicate.core.resources.cloud_watch_alarm_resource import \
    CloudWatchAlarmResource
from syndicate.core.resources.cloud_watch_resource import CloudWatchResource
from syndicate.core.resources.cognito_resource import CognitoResource
from syndicate.core.resources.dynamo_db_resource import DynamoDBResource
from syndicate.core.resources.ebs_resource import EbsResource
from syndicate.core.resources.ec2_resource import Ec2Resource
from syndicate.core.resources.iam_resource import IamResource
from syndicate.core.resources.kinesis_resource import KinesisResource
from syndicate.core.resources.lambda_resource import LambdaResource
from syndicate.core.resources.s3_resource import S3Resource
from syndicate.core.resources.sns_resource import SnsResource
from syndicate.core.resources.sqs_resource import SqsResource
from syndicate.core.resources.step_functions_resource import \
    StepFunctionResource


class ResourceProvider:
    instance = None

    def __init__(self, config, credentials, sts_conn) -> None:
        self.sts_conn = sts_conn
        if not ResourceProvider.instance:
            ResourceProvider.instance = ResourceProvider.__Resources(
                config=config,
                credentials=credentials
            )

    def sts(self):
        return self.sts_conn

    def __getattr__(self, item):
        return getattr(self.instance, item)

    class __Resources:

        _conn_provider = None

        _cw_alarm_resource = None
        _cw_resource = None
        _sns_resource = None
        _api_gateway_resource = None
        _cognito_resource = None
        _dynamodb_resource = None
        _ebs_resource = None
        _ec2_resource = None
        _iam_resource = None
        _kinesis_resource = None
        _lambda_resource = None
        _s3_resource = None
        _sqs_resource = None
        _step_functions_resource = None

        def __init__(self, config, credentials) -> None:
            self.credentials = credentials
            self._conn_provider = ConnectionProvider(credentials)
            self.config = config

        def cw_alarm(self, region=None):
            if not region:
                region = self.credentials.get('region')
            if not self._cw_alarm_resource:
                self._cw_alarm_resource = CloudWatchAlarmResource(
                    cw_conn=self._conn_provider.cw_metric(region=region),
                    sns_conn=self._conn_provider.sqs()
                )
            return self._cw_alarm_resource

        def cw(self):
            if not self._cw_resource:
                self._cw_resource = CloudWatchResource(
                    cw_events_conn_builder=self._conn_provider.cw_events,
                    account_id=self.config.account_id
                )
            return self._cw_resource

        def sns(self):
            if not self._sns_resource:
                self._sns_resource = SnsResource(
                    conn_provider=self._conn_provider,
                    region=self.credentials.get('region'))
            return self._sns_resource

        def api_gw(self):
            if not self._api_gateway_resource:
                self._api_gateway_resource = ApiGatewayResource(
                    apigw_conn=self._conn_provider.api_gateway(),
                    lambda_res=self.lambda_resource(),
                    account_id=self.config.account_id,
                    region=self.config.region
                )
            return self._api_gateway_resource

        def cognito(self):
            self._cognito_resource = CognitoResource(
                cognito_conn=self._conn_provider.cognito_identity(),
                account_id=self.config.account_id,
                region=self.config.region
            )
            if not self._cognito_resource:
                pass
            return self._cognito_resource

        def dynamodb(self):
            if not self._dynamodb_resource:
                self._dynamodb_resource = DynamoDBResource(
                    dynamodb_conn=self._conn_provider.dynamodb(),
                    cw_alarm_conn=self._conn_provider.cw_metric(),
                    app_as_conn=self._conn_provider.application_autoscaling(),
                    iam_conn=self._conn_provider.iam()
                )
            return self._dynamodb_resource

        def ebs(self):
            if not self._ebs_resource:
                self._ebs_resource = EbsResource(
                    ec2_conn=self._conn_provider.ec2(),
                    iam_conn=self._conn_provider.iam(),
                    ebs_conn=self._conn_provider.beanstalk(),
                    sns_conn=self._conn_provider.sns(),
                    s3_conn=self._conn_provider.s3(),
                    account_id=self.config.account_id,
                    region=self.config.region,
                    deploy_target_bucket=self.config.deploy_target_bucket
                )
            return self._ebs_resource

        def ec2(self):
            if not self._ec2_resource:
                self._ec2_resource = Ec2Resource(
                    ec2_conn=self._conn_provider.ec2(),
                    iam_conn=self._conn_provider.iam(),
                    account_id=self.config.account_id,
                    region=self.config.region
                )
            return self._ec2_resource

        def iam(self):
            if not self._iam_resource:
                self._iam_resource = IamResource(
                    iam_conn=self._conn_provider.iam(),
                    account_id=self.config.account_id,
                    region=self.config.region
                )
            return self._iam_resource

        def kinesis(self):
            if not self._kinesis_resource:
                self._kinesis_resource = KinesisResource(
                    kin_conn=self._conn_provider.kinesis()
                )
            return self._kinesis_resource

        def lambda_resource(self):
            if not self._lambda_resource:
                self._lambda_resource = LambdaResource(
                    lambda_conn=self._conn_provider.lambda_conn(),
                    s3_conn=self._conn_provider.s3(),
                    cw_logs_conn=self._conn_provider.cw_logs(),
                    sns_conn=self.sns(),
                    iam_conn=self._conn_provider.iam(),
                    dynamodb_conn=self._conn_provider.dynamodb(),
                    sqs_conn=self._conn_provider.sqs(),
                    kinesis_conn=self._conn_provider.kinesis(),
                    cw_events_conn=self._conn_provider.cw_events(),
                    region=self.config.region,
                    account_id=self.config.account_id,
                    deploy_target_bucket=self.config.deploy_target_bucket
                )
            return self._lambda_resource

        def s3(self):
            if not self._s3_resource:
                self._s3_resource = S3Resource(
                    s3_conn=self._conn_provider.s3()
                )
            return self._s3_resource

        def sqs(self):
            if not self._sqs_resource:
                self._sqs_resource = SqsResource(
                    sqs_conn_builder=self._conn_provider.sqs,
                    region=self.config.region,
                    account_id=self.config.account_id
                )
            return self._sqs_resource

        def step_functions(self):
            if not self._step_functions_resource:
                self._step_functions_resource = StepFunctionResource(
                    sf_conn=self._conn_provider.step_functions(),
                    iam_conn=self._conn_provider.iam(),
                    cw_events_conn=self._conn_provider.cw_events(),
                    lambda_conn=self._conn_provider.lambda_conn(),
                    region=self.config.region,
                    account_id=self.config.account_id
                )
            return self._step_functions_resource
