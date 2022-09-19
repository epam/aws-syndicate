#  Copyright 2021 EPAM Systems, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from syndicate.core.transform.terraform.converter.tf_lambda_layer_converter import \
    LambdaLayerConverter
from syndicate.commons.log_helper import get_logger
from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer
from syndicate.core.transform.terraform.converter.tf_api_gateway_converter import \
    ApiGatewayConverter
from syndicate.core.transform.terraform.converter.tf_batch_compenv_converter import \
    BatchComputeEnvConverter
from syndicate.core.transform.terraform.converter.tf_batch_jobdef_converter import \
    BatchJobDefConverter
from syndicate.core.transform.terraform.converter.tf_batch_jobqueue_converter import \
    BatchJobQueueEnvConverter
from syndicate.core.transform.terraform.converter.tf_cloud_watch_alram_converter import \
    CloudWatchAlarmConverter
from syndicate.core.transform.terraform.converter.tf_cloud_watch_rule_converter import \
    CloudWatchRuleConverter
from syndicate.core.transform.terraform.converter.tf_cognito_converter import \
    CognitoConverter
from syndicate.core.transform.terraform.converter.tf_dynamo_db_converter import \
    DynamoDbConverter
from syndicate.core.transform.terraform.converter.tf_iam_policy_converter import \
    IamPolicyConverter
from syndicate.core.transform.terraform.converter.tf_iam_role_converter import \
    IamRoleConverter
from syndicate.core.transform.terraform.converter.tf_kinesis_stream_converter import \
    KinesisStreamConverter
from syndicate.core.transform.terraform.converter.tf_lambda_converter import \
    LambdaConverter
from syndicate.core.transform.terraform.converter.tf_s3_bucket_converter import \
    S3BucketConverter
from syndicate.core.transform.terraform.converter.tf_sns_app_converter import \
    SNSApplicationConverter
from syndicate.core.transform.terraform.converter.tf_sns_topic_converter import \
    SNSTopicConverter
from syndicate.core.transform.terraform.converter.tf_sqs_converter import \
    SQSQueueConverter
from syndicate.core.transform.terraform.terraform_template import \
    TerraformTemplate

READ_CAPACITY_UNITS = 'ReadCapacityUnits'
WRITE_CAPACITY_UNITS = 'WriteCapacityUnits'

_LOG = get_logger('syndicate.core.transform.terraform_transformer')


class TerraformTransformer(BuildMetaTransformer):

    def __init__(self, bundle_name=None):
        super().__init__(bundle_name)
        self.template = TerraformTemplate('aws', 'default', self.config.region)

    def add_resource(self, transformed_resource):
        pass  # TODO implement or design other approach

    def output_file_name(self) -> str:
        return 'terraform_template.tf.json'

    def _transform_iam_managed_policy(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=IamPolicyConverter,
                               name=name)

    def _transform_iam_role(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=IamRoleConverter,
                               name=name)

    def _transform_lambda(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=LambdaConverter,
                               name=name)

    def _transform_dynamo_db_table(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=DynamoDbConverter,
                               name=name)

    def _transform_s3_bucket(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=S3BucketConverter,
                               name=name)

    def _transform_cloud_watch_rule(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=CloudWatchRuleConverter,
                               name=name)

    def _transform_api_gateway(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=ApiGatewayConverter,
                               name=name)

    def _transform_sns_topic(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=SNSTopicConverter,
                               name=name)

    def _transform_sqs_queue(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=SQSQueueConverter,
                               name=name)

    def _transform_cloudwatch_alarm(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=CloudWatchAlarmConverter,
                               name=name)

    def _transform_kinesis_stream(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=KinesisStreamConverter,
                               name=name)

    def _transform_sns_application(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=SNSApplicationConverter,
                               name=name)

    def _transform_cognito(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=CognitoConverter,
                               name=name)

    def _transform_batch_compenv(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=BatchComputeEnvConverter,
                               name=name)

    def _transform_batch_jobqueue(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=BatchJobQueueEnvConverter,
                               name=name)

    def _transform_batch_jobdef(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=BatchJobDefConverter,
                               name=name)

    def _transform_lambda_layer(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=LambdaLayerConverter,
                               name=name)

    def convert_resources(self, name, resource, converter_type):
        converter = converter_type(template=self.template, config=self.config,
                                   resources_provider=self.resources_provider)
        converter.convert(name=name, resource=resource)

    def _compose_template(self):
        return self.template.compose_resources()
