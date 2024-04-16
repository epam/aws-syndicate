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
from syndicate.core.resources.cloud_watch_alarm_resource import (
    CloudWatchAlarmResource)
from syndicate.core.resources.cloud_watch_resource import CloudWatchResource
from syndicate.core.resources.cognito_identity_resource import (
    CognitoIdentityResource)
from syndicate.core.resources.cognito_user_pool_resource import (
    CognitoUserPoolResource)
from syndicate.core.resources.docdb_cluster_resource import \
    DocumentDBClusterResource
from syndicate.core.resources.docdb_instance_resource import \
    DocumentDBInstanceResource
from syndicate.core.resources.dynamo_db_resource import DynamoDBResource
from syndicate.core.resources.dax_resource import DaxResource
from syndicate.core.resources.ebs_resource import EbsResource
from syndicate.core.resources.ec2_resource import Ec2Resource
from syndicate.core.resources.firehose_resource import FirehoseResource
from syndicate.core.resources.eventbridge_scheduler_resource import EventBridgeSchedulerResource
from syndicate.core.resources.iam_resource import IamResource
from syndicate.core.resources.kinesis_resource import KinesisResource
from syndicate.core.resources.lambda_resource import LambdaResource
from syndicate.core.resources.s3_resource import S3Resource
from syndicate.core.resources.sns_resource import SnsResource
from syndicate.core.resources.sqs_resource import SqsResource
from syndicate.core.resources.step_functions_resource import (
    StepFunctionResource)
from syndicate.core.resources.batch_compenv_resource import (
    BatchComputeEnvironmentResource)
from syndicate.core.resources.batch_jobqueue_resource import (
    BatchJobQueueResource)
from syndicate.core.resources.batch_jobdef_resource import (
    BatchJobDefinitionResource)
from syndicate.core.resources.group_tagging_api_resource import TagsApiResource
from syndicate.core.resources.swagger_ui_resource import SwaggerUIResource


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
        _cognito_identity_resource = None
        _cognito_user_pool_resource = None
        _dynamodb_resource = None
        _ebs_resource = None
        _ec2_resource = None
        _firehose_resource = None
        _iam_resource = None
        _kinesis_resource = None
        _lambda_resource = None
        _s3_resource = None
        _sqs_resource = None
        _step_functions_resource = None
        _batch_compenv_resource = None
        _batch_jobqueue_resource = None
        _batch_jobdef_resource = None
        _documentdb_cluster_resource = None
        _documentdb_instance_resource = None
        _tags_api_resource = None
        _dax_cluster_resource = None
        _eventbridge_scheduler_resource = None
        _swagger_ui_resource = None

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
                    sns_conn=self._conn_provider.sns(),
                    lambda_conn=self._conn_provider.lambda_conn(),
                    lambda_res=self.lambda_resource(),
                    account_id=self.config.account_id
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
                    apigw_v2_conn=self._conn_provider.api_gateway_v2(),
                    lambda_res=self.lambda_resource(),
                    cognito_res=self.cognito_user_pool(),
                    account_id=self.config.account_id,
                    region=self.config.region
                )
            return self._api_gateway_resource

        def cognito_identity(self):
            self._cognito_identity_resource = CognitoIdentityResource(
                cognito_conn=self._conn_provider.cognito_identity(),
                account_id=self.config.account_id,
                region=self.config.region
            )
            if not self._cognito_identity_resource:
                pass
            return self._cognito_identity_resource

        def cognito_user_pool(self):
            self._cognito_user_pool_resource = CognitoUserPoolResource(
                cognito_idp_conn=
                self._conn_provider.cognito_identity_provider(),
                account_id=self.config.account_id,
                region=self.config.region
            )
            if not self._cognito_user_pool_resource:
                pass
            return self._cognito_user_pool_resource

        def dynamodb(self):
            if not self._dynamodb_resource:
                self._dynamodb_resource = DynamoDBResource(
                    dynamodb_conn=self._conn_provider.dynamodb(),
                    cw_alarm_conn=self._conn_provider.cw_metric(),
                    app_as_conn=self._conn_provider.application_autoscaling(),
                    iam_conn=self._conn_provider.iam()
                )
            return self._dynamodb_resource

        def dax_cluster(self):
            if not self._dax_cluster_resource:
                self._dax_cluster_resource = DaxResource(
                    dax_conn=self._conn_provider.dax(),
                    iam_conn=self._conn_provider.iam()
                )
            return self._dax_cluster_resource

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

        def firehose(self):
            if not self._firehose_resource:
                self._firehose_resource = FirehoseResource(
                    firehose_conn=self._conn_provider.firehose(),
                    s3_resource=self.s3(),
                    iam_resource=self.iam()
                )
            return self._firehose_resource

        def eventbridge_scheduler(self):
            if not self._eventbridge_scheduler_resource:
                self._eventbridge_scheduler_resource = EventBridgeSchedulerResource(
                    eventbridge_conn=self._conn_provider.eventbridge_scheduler()
                )
            return self._eventbridge_scheduler_resource

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
                    s3_conn=self._conn_provider.s3(),
                    account_id=self.config.account_id
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

        def batch_compenv(self):
            if not self._batch_compenv_resource:
                self._batch_compenv_resource = BatchComputeEnvironmentResource(
                    batch_conn=self._conn_provider.batch(),
                    iam_conn=self._conn_provider.iam(),
                    region=self.config.region,
                    account_id=self.config.account_id
                )
            return self._batch_compenv_resource

        def batch_jobqueue(self):
            if not self._batch_jobqueue_resource:
                self._batch_jobqueue_resource = BatchJobQueueResource(
                    batch_conn=self._conn_provider.batch()
                )
            return self._batch_jobqueue_resource

        def batch_jobdef(self):
            if not self._batch_jobdef_resource:
                self._batch_jobdef_resource = BatchJobDefinitionResource(
                    batch_conn=self._conn_provider.batch(),
                    iam_conn=self._conn_provider.iam()
                )
            return self._batch_jobdef_resource

        def documentdb_cluster(self):
            if not self._documentdb_cluster_resource:
                self._documentdb_cluster_resource = DocumentDBClusterResource(
                    docdb_conn=self._conn_provider.documentdb(),
                    region=self.config.region,
                    account_id=self.config.account_id
                )
            return self._documentdb_cluster_resource

        def documentdb_instance(self):
            if not self._documentdb_instance_resource:
                self._documentdb_instance_resource = \
                    DocumentDBInstanceResource(
                        docdb_conn=self._conn_provider.documentdb(),
                        region=self.config.region,
                        account_id=self.config.account_id
                    )
            return self._documentdb_instance_resource

        def tags_api(self):
            if not self._tags_api_resource:
                self._tags_api_resource = TagsApiResource(
                    connection=self._conn_provider.groups_tagging_api()
                )
            return self._tags_api_resource

        def swagger_ui(self):
            if not self._swagger_ui_resource:
                self._swagger_ui_resource = SwaggerUIResource(
                    s3_conn=self._conn_provider.s3(),
                    deploy_target_bucket=self.config.deploy_target_bucket,
                    deploy_target_bucket_key_compound=(
                        self.config.deploy_target_bucket_key_compound),
                    region=self.config.region,
                    account_id=self.config.account_id,
                    extended_prefix_mode=self.config.extended_prefix_mode,
                    prefix=self.config.resources_prefix,
                    suffix=self.config.resources_suffix
                )
            return self._swagger_ui_resource
