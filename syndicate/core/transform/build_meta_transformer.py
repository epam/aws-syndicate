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
from abc import abstractmethod, ABC
from functools import cmp_to_key

from syndicate.commons.log_helper import get_user_logger
from syndicate.core.build.deployment_processor import compare_deploy_resources
from syndicate.core.build.meta_processor import resolve_meta, populate_s3_paths
from syndicate.core.constants import \
    (IAM_POLICY, IAM_ROLE, LAMBDA_TYPE, DYNAMO_TABLE_TYPE, S3_BUCKET_TYPE,
     CLOUD_WATCH_RULE_TYPE, SQS_QUEUE_TYPE, API_GATEWAY_TYPE, SNS_TOPIC_TYPE,
     CLOUD_WATCH_ALARM_TYPE, KINESIS_STREAM_TYPE, COGNITO_FEDERATED_POOL_TYPE,
     SNS_PLATFORM_APPLICATION_TYPE, BATCH_COMPENV_TYPE, BATCH_JOBQUEUE_TYPE,
     BATCH_JOBDEF_TYPE, LAMBDA_LAYER_TYPE)

_LOG = get_user_logger()


class BuildMetaTransformer(ABC):

    def __init__(self, bundle_name=None):
        from syndicate.core import CONFIG, RESOURCES_PROVIDER
        self.config = CONFIG
        self.resources_provider = RESOURCES_PROVIDER

        self.transformer_mapping = {
            IAM_POLICY: self._transform_iam_managed_policy,
            IAM_ROLE: self._transform_iam_role,
            LAMBDA_TYPE: self._transform_lambda,
            LAMBDA_LAYER_TYPE: self._transform_lambda_layer,
            DYNAMO_TABLE_TYPE: self._transform_dynamo_db_table,
            S3_BUCKET_TYPE: self._transform_s3_bucket,
            CLOUD_WATCH_RULE_TYPE: self._transform_cloud_watch_rule,
            SQS_QUEUE_TYPE: self._transform_sqs_queue,
            API_GATEWAY_TYPE: self._transform_api_gateway,
            SNS_TOPIC_TYPE: self._transform_sns_topic,
            SNS_PLATFORM_APPLICATION_TYPE: self._transform_sns_application,
            CLOUD_WATCH_ALARM_TYPE: self._transform_cloudwatch_alarm,
            KINESIS_STREAM_TYPE: self._transform_kinesis_stream,
            COGNITO_FEDERATED_POOL_TYPE: self._transform_cognito,
            BATCH_COMPENV_TYPE: self._transform_batch_compenv,
            BATCH_JOBQUEUE_TYPE: self._transform_batch_jobqueue,
            BATCH_JOBDEF_TYPE: self._transform_batch_jobdef
        }
        self.bundle_name = bundle_name

    def transform_build_meta(self, build_meta):
        build_meta = resolve_meta(build_meta)
        build_meta = populate_s3_paths(build_meta, self.bundle_name)
        resources_list = list(build_meta.items())
        resources_list.sort(key=cmp_to_key(compare_deploy_resources))
        for name, resource in resources_list:
            resource_type = resource.get('resource_type')
            transformer = self.transformer_mapping.get(resource_type)
            if transformer is None:
                _LOG.warning("Transformation is not supported for resources "
                    "of the '{}' type".format(resource_type))
                continue
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
    def _transform_lambda_layer(self, name, resource):
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
    def _transform_sqs_queue(self, name, resource):
        pass

    @abstractmethod
    def _transform_kinesis_stream(self, name, resource):
        pass

    @abstractmethod
    def _transform_sns_application(self, name, resource):
        pass

    @abstractmethod
    def _transform_cognito(self, name, resource):
        pass

    @abstractmethod
    def _transform_batch_compenv(self, name, resource):
        pass

    @abstractmethod
    def _transform_batch_jobqueue(self, name, resource):
        pass

    @abstractmethod
    def _transform_batch_jobdef(self, name, resource):
        pass

    @abstractmethod
    def _compose_template(self):
        pass
