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
from abc import abstractmethod
from functools import cmp_to_key

from syndicate.core.build.deployment_processor import compare_deploy_resources
from syndicate.core.build.meta_processor import resolve_meta
from syndicate.core.constants import (IAM_POLICY, IAM_ROLE, LAMBDA_TYPE,
                                      API_GATEWAY_TYPE)
from syndicate.core.constants import IAM_POLICY, IAM_ROLE, LAMBDA_TYPE, \
    DYNAMO_TABLE_TYPE, S3_BUCKET_TYPE, CLOUD_WATCH_RULE_TYPE, SQS_QUEUE_TYPE, \
    API_GATEWAY_TYPE, SNS_TOPIC_TYPE, CLOUD_WATCH_ALARM_TYPE, \
    EC2_INSTANCE_TYPE


class BuildMetaTransformer(object):

    def __init__(self):
        from syndicate.core import CONFIG, RESOURCES_PROVIDER
        self.config = CONFIG
        self.resources_provider = RESOURCES_PROVIDER

        self.resources = list()
        self.transformer_mapping = {
            IAM_POLICY: self._transform_iam_managed_policy,
            IAM_ROLE: self._transform_iam_role,
            LAMBDA_TYPE: self._transform_lambda,
            DYNAMO_TABLE_TYPE: self._transform_dynamo_db_table,
            S3_BUCKET_TYPE: self._transform_s3_bucket,
            CLOUD_WATCH_RULE_TYPE: self._transform_cloud_watch_rule,
            SQS_QUEUE_TYPE: self._transform_sqs_queue,
            API_GATEWAY_TYPE: self._transform_api_gateway,
            SNS_TOPIC_TYPE: self._transform_sns_topic,
            CLOUD_WATCH_ALARM_TYPE: self._transform_cloudwatch_alarm,
            EC2_INSTANCE_TYPE: self._transform_ec2_instance,
        }

    def transform_build_meta(self, build_meta):
        build_meta = resolve_meta(build_meta)
        resources_list = list(build_meta.items())
        resources_list.sort(key=cmp_to_key(compare_deploy_resources))
        for name, resource in resources_list:
            resource_type = resource.get('resource_type')
            transformer = self.transformer_mapping.get(resource_type)
            if transformer is None:
                raise ValueError(
                    "Transformation is not supported for resources "
                    "of the '{}' type".format(resource_type))
            transformer(name=name, resource=resource)
        return self._compose_template()

    @abstractmethod
    def output_file_name(self) -> str:
        pass

    @abstractmethod
    def _transform_iam_managed_policy(self, name, resource):
        pass

    @abstractmethod
    def _transform_iam_role(self, name, resource):
        pass

    @abstractmethod
    def _transform_lambda(self, name, resource):
        pass

    @abstractmethod
    def _transform_dynamo_db_table(self, name, resource):
        pass

    @abstractmethod
    def _transform_s3_bucket(self, name, resource):
        pass

    @abstractmethod
    def _transform_cloud_watch_rule(self, name, resource):
        pass

    @abstractmethod
    def _transform_api_gateway(self, name, resource):
        pass

    @abstractmethod
    def _transform_sns_topic(self, name, resource):
        pass

    @abstractmethod
    def _transform_cloudwatch_alarm(self, name, resource):
        pass

    @abstractmethod
    def _transform_ec2_instance(self, name, resource):
        pass

    @abstractmethod
    def _transform_sqs_queue(self, name, resource):
        pass

    @abstractmethod
    def _transform_dynamodb_stream(self, name, resource):
        pass

    @abstractmethod
    def _compose_template(self):
        pass
