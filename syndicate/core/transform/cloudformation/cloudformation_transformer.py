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
from troposphere import Template

from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer
from .converter.cf_api_gateway_converter import CfApiGatewayConverter
from .converter.cf_batch_compenv_converter import \
    CfBatchComputeEnvironmentConverter
from .converter.cf_batch_job_defeinition import CfBatchJobDefinitionConverter
from .converter.cf_batch_job_queue_converter import CfBatchJobQueueConverter
from .converter.cf_cloudwatch_alarm_converter import CfCloudWatchAlarmConverter
from .converter.cf_cloudwatch_rule_converter import CfCloudWatchRuleConverter
from .converter.cf_cognito_converter import CfCognitoConverter
from .converter.cf_dynamodb_table_converter import CfDynamoDbTableConverter
from .converter.cf_iam_managed_policy_converter import \
    CfIamManagedPolicyConverter
from .converter.cf_iam_role_converter import CfIamRoleConverter
from .converter.cf_kinesis_stream_converter import CfKinesisStreamConverter
from .converter.cf_lambda_function_converter import CfLambdaFunctionConverter
from .converter.cf_lambda_layer_converter import CfLambdaLayerConverter
from .converter.cf_s3_converter import CfS3Converter
from .converter.cf_sns_converter import CfSnsConverter
from .converter.cf_sqs_converter import CfSqsConverter


class CloudFormationTransformer(BuildMetaTransformer):

    def __init__(self, bundle_name):
        super().__init__(bundle_name)
        self.template = Template()

    def output_file_name(self) -> str:
        return 'cloudformation_template.yaml'

    def _transform_iam_managed_policy(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfIamManagedPolicyConverter)

    def _transform_iam_role(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfIamRoleConverter)

    def _transform_lambda(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfLambdaFunctionConverter)

    def _transform_lambda_layer(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfLambdaLayerConverter)

    def _transform_dynamo_db_table(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfDynamoDbTableConverter)

    def _transform_s3_bucket(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfS3Converter)

    def _transform_cloud_watch_rule(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfCloudWatchRuleConverter)

    def _transform_api_gateway(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfApiGatewayConverter)

    def _transform_sns_topic(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfSnsConverter)

    def _transform_sns_application(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfSqsConverter)

    def _transform_cognito(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfCognitoConverter)

    def _transform_cloudwatch_alarm(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfCloudWatchAlarmConverter)

    def _transform_sqs_queue(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfSqsConverter)

    def _transform_kinesis_stream(self, name, resource):
        self.convert_resources(name=name,
                               resource=resource,
                               converter_type=CfKinesisStreamConverter)

    def _transform_batch_compenv(self, name, resource):
        self.convert_resources(
            name=name,
            resource=resource,
            converter_type=CfBatchComputeEnvironmentConverter)

    def _transform_batch_jobqueue(self, name, resource):
        self.convert_resources(
            name=name,
            resource=resource,
            converter_type=CfBatchJobQueueConverter)

    def _transform_batch_jobdef(self, name, resource):
        self.convert_resources(
            name=name,
            resource=resource,
            converter_type=CfBatchJobDefinitionConverter)

    def convert_resources(self, name, resource, converter_type):
        converter = converter_type(
            template=self.template,
            config=self.config,
            resources_provider=self.resources_provider)
        converter.convert(name=name, meta=resource)

    def _compose_template(self):
        return self.template.to_yaml()
