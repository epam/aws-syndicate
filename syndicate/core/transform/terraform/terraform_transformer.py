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

from core.transform.terraform.converter.api_gateway_converter import \
    ApiGatewayConverter
from core.transform.terraform.converter.dynamo_db_converter import \
    DynamoDbConverter
from core.transform.terraform.converter.iam_policy_converter import \
    IamPolicyConverter
from core.transform.terraform.converter.iam_role_converter import \
    IamRoleConverter
from core.transform.terraform.converter.lambda_converter import LambdaConverter
from syndicate.commons.log_helper import get_logger
from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer
from syndicate.core.transform.terraform.terraform_template import \
    TerraformTemplate

READ_CAPACITY_UNITS = 'ReadCapacityUnits'
WRITE_CAPACITY_UNITS = 'WriteCapacityUnits'

_LOG = get_logger('syndicate.core.transform.terraform_transformer')


class TerraformTransformer(BuildMetaTransformer):

    def __init__(self):
        super().__init__()
        self.template = TerraformTemplate('aws', 'default', self.config.region)

    def add_resource(self, transformed_resource):
        pass  # TODO implement or design other approach

    def output_file_name(self) -> str:
        return 'terraform_template.tf.json'

    def _transform_iam_managed_policy(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=IamPolicyConverter)

    def _transform_iam_role(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=IamRoleConverter)

    def _transform_lambda(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=LambdaConverter)

    def _transform_dynamo_db_table(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=DynamoDbConverter)

    def _transform_s3_bucket(self, name, resource):
        location = resource.get('location')
        acl = resource.get('acl')
        policy = resource.get('policy')

        pass

    def _transform_cloud_watch_rule(self, name, resource):
        rule_type = resource.get('rule_type')
        expression = resource.get('expression')
        region = resource.get('region')

        pass

    def _transform_api_gateway(self, name, resource):
        self.convert_resources(resource=resource,
                               converter_type=ApiGatewayConverter)

    def convert_resources(self, resource, converter_type):
        converter = converter_type(template=self.template, config=self.config)
        converter.convert(resource=resource)

    def _transform_sns_topic(self, name, resource):
        deploy_stage = resource.get('deploy_stage')
        region = resource.get('region')
        event_sources = resource.get('event_sources')

        pass

    def _transform_cloudwatch_alarm(self, name, resource):
        metric_name = resource.get('metric_name')
        period = resource.get('period')
        evaluation_periods = resource.get('evaluation_periods')
        threshold = resource.get('threshold')
        comparison_operator = resource.get('comparison_operator')
        statistic = resource.get('statistic')
        sns_topics = resource.get('sns_topics')

        pass

    def _transform_ec2_instance(self, name, resource):
        metric_name = resource.get('metric_name')
        period = resource.get('period')
        evaluation_periods = resource.get('evaluation_periods')
        threshold = resource.get('threshold')
        comparison_operator = resource.get('comparison_operator')
        statistic = resource.get('statistic')
        sns_topics = resource.get('sns_topics')

        pass

    def _transform_sqs_queue(self, name, resource):
        pass

    def _transform_dynamodb_stream(self, name, resource):
        table_name = resource.get('table')
        stream_view_type = resource.get('stream_view_type')

        pass

    def _compose_template(self):
        return self.template.compose_resources()
