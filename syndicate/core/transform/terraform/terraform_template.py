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
import json

PROVIDER_KEY = 'provider'
RESOURCE_KEY = 'resource'

LAMBDA_RESOURCE_NAME = 'aws_lambda_function'
IAM_POLICY_RESOURCE_NAME = 'aws_iam_policy'
IAM_ROLE_RESOURCE_NAME = 'aws_iam_role'
DYNAMO_DB_TABLE_RESOURCE_NAME = 'aws_dynamodb_table'
APP_AUTOSCALING_TARGET_RESOURCE_NAME = 'aws_appautoscaling_target'
APP_AUTOSCALING_POLICY_RESOURCE_NAME = 'aws_appautoscaling_policy'
API_GATEWAY_REST_API_RESOURCE_NAME = 'aws_api_gateway_rest_api'
API_GATEWAY_RESOURCE_RESOURCE_NAME = 'aws_api_gateway_resource'
API_GATEWAY_METHOD_RESPONSE_RESOURCE_NAME = 'aws_api_gateway_method_response'
API_GATEWAY_INTEGRATION_RESOURCE_NAME = 'aws_api_gateway_integration'
API_GATEWAY_STAGE_RESOURCE_NAME = 'aws_api_gateway_stage'
API_GATEWAY_DEPLOYMENT_RESOURCE_NAME = 'aws_api_gateway_deployment'
API_GATEWAY_INTEGRATION_RESPONSE_RESOURCE_NAME = 'aws_api_gateway_integration_response'
API_GATEWAY_METHOD_RESOURCE_NAME = 'aws_api_gateway_method'
S3_BUCKET_RESOURCE_NAME = 'aws_s3_bucket'
CLOUD_WATCH_EVENT_RULE = 'aws_cloudwatch_event_rule'
CLOUD_WATCH_EVENT_TARGET = 'aws_cloudwatch_event_target'
SNS_TOPIC_RESOURCE = 'aws_sns_topic'
SQS_QUEUE_RESOURCE = 'aws_sqs_queue'
CLOUD_WATCH_ALARM = 'aws_cloudwatch_metric_alarm'
KINESIS_STREAM_RESOURCE = 'aws_kinesis_stream'
SNS_APPLICATION_RESOURCE = 'aws_sns_platform_application'
AWS_API_GATEWAY_AUTHORIZER = 'aws_api_gateway_authorizer'
AWS_COGNITO_IDENTITY_POOL = 'aws_cognito_identity_pool'
AWS_COGNITO_IDENTITY_POOL_ROLES_ATTACHMENT = 'aws_cognito_identity_pool_roles_attachment'
AWS_LAMBDA_PROVISIONED_CONCURRENCY_CONFIG = 'aws_lambda_provisioned_concurrency_config'
AWS_LAMBDA_ALIAS = 'aws_lambda_alias'
CLOUD_WATCH_LOG_GROUP = 'aws_cloudwatch_log_group'
SNS_TOPIC_POLICY = 'aws_sns_topic_policy'
AWS_BATCH_JOB_DEFINITION = 'aws_batch_job_definition'
AWS_BATCH_COMPUTE_ENVIRONMENT = 'aws_batch_compute_environment'
AWS_BATCH_JOB_QUEUE = 'aws_batch_job_queue'
AWS_IAM_INSTANCE_PROFILE = 'aws_iam_instance_profile'
AWS_IAM_ROLE_POLICY_ATTACHMENT = 'aws_iam_role_policy_attachment'
AWS_LAMBDA_EVENT_SOURCE_MAPPING = 'aws_lambda_event_source_mapping'
AWS_IAM_ROLE_POLICY = 'aws_iam_role_policy'
AWS_SNS_TOPIC_SUBSCRIPTION = 'aws_sns_topic_subscription'
AWS_LAMBDA_PERMISSION = 'aws_lambda_permission'
AWS_S3_BUCKET_NOTIFICATION = 'aws_s3_bucket_notification'
AWS_SQS_POLICY = 'aws_sqs_queue_policy'
AWS_API_GATEWAY_REQUEST_VALIDATOR = 'aws_api_gateway_request_validator'
AWS_LAMBDA_LAYER_VERSION = 'aws_lambda_layer_version'

RESOURCE_TYPES = [LAMBDA_RESOURCE_NAME, IAM_POLICY_RESOURCE_NAME,
                  IAM_ROLE_RESOURCE_NAME, DYNAMO_DB_TABLE_RESOURCE_NAME,
                  APP_AUTOSCALING_TARGET_RESOURCE_NAME,
                  APP_AUTOSCALING_POLICY_RESOURCE_NAME,
                  API_GATEWAY_REST_API_RESOURCE_NAME,
                  API_GATEWAY_RESOURCE_RESOURCE_NAME,
                  API_GATEWAY_METHOD_RESPONSE_RESOURCE_NAME,
                  API_GATEWAY_INTEGRATION_RESOURCE_NAME,
                  API_GATEWAY_STAGE_RESOURCE_NAME,
                  API_GATEWAY_DEPLOYMENT_RESOURCE_NAME,
                  API_GATEWAY_INTEGRATION_RESPONSE_RESOURCE_NAME,
                  API_GATEWAY_METHOD_RESOURCE_NAME, S3_BUCKET_RESOURCE_NAME,
                  CLOUD_WATCH_EVENT_RULE, CLOUD_WATCH_EVENT_TARGET,
                  SNS_TOPIC_RESOURCE, SQS_QUEUE_RESOURCE, CLOUD_WATCH_ALARM,
                  KINESIS_STREAM_RESOURCE, SNS_APPLICATION_RESOURCE,
                  AWS_API_GATEWAY_AUTHORIZER, AWS_COGNITO_IDENTITY_POOL,
                  AWS_COGNITO_IDENTITY_POOL_ROLES_ATTACHMENT,
                  AWS_LAMBDA_PROVISIONED_CONCURRENCY_CONFIG, AWS_LAMBDA_ALIAS,
                  CLOUD_WATCH_LOG_GROUP, SNS_TOPIC_POLICY,
                  AWS_BATCH_JOB_DEFINITION, AWS_BATCH_COMPUTE_ENVIRONMENT,
                  AWS_BATCH_JOB_QUEUE, AWS_IAM_INSTANCE_PROFILE,
                  AWS_IAM_ROLE_POLICY_ATTACHMENT,
                  AWS_LAMBDA_EVENT_SOURCE_MAPPING,
                  AWS_IAM_ROLE_POLICY, AWS_SNS_TOPIC_SUBSCRIPTION,
                  AWS_LAMBDA_PERMISSION, AWS_S3_BUCKET_NOTIFICATION,
                  AWS_SQS_POLICY, AWS_API_GATEWAY_REQUEST_VALIDATOR,
                  AWS_LAMBDA_LAYER_VERSION]


class TerraformTemplate(object):

    def __init__(self, provider, profile, region):
        self.aws_lambda_function = []
        self.aws_iam_policy = []
        self.aws_iam_role = []
        self.aws_dynamodb_table = []
        self.aws_appautoscaling_target = []
        self.aws_appautoscaling_policy = []
        self.aws_api_gateway_rest_api = []
        self.aws_api_gateway_resource = []
        self.aws_api_gateway_method_response = []
        self.aws_api_gateway_integration = []
        self.aws_api_gateway_stage = []
        self.aws_api_gateway_deployment = []
        self.aws_api_gateway_integration_response = []
        self.aws_api_gateway_method = []
        self.aws_s3_bucket = []
        self.aws_cloudwatch_event_rule = []
        self.aws_cloudwatch_event_target = []
        self.aws_sns_topic = []
        self.aws_sqs_queue = []
        self.aws_cloudwatch_metric_alarm = []
        self.aws_kinesis_stream = []
        self.aws_sns_platform_application = []
        self.aws_api_gateway_authorizer = []
        self.aws_cognito_identity_pool = []
        self.aws_cognito_identity_pool_roles_attachment = []
        self.aws_lambda_provisioned_concurrency_config = []
        self.aws_lambda_alias = []
        self.cloud_watch_log_group = []
        self.aws_sns_topic_policy = []
        self.aws_batch_job_definition = []
        self.aws_batch_compute_environment = []
        self.aws_batch_job_queue = []
        self.aws_iam_instance_profile = []
        self.aws_iam_role_policy_attachment = []
        self.aws_lambda_event_source_mapping = []
        self.aws_iam_role_policy = []
        self.aws_sns_topic_subscription = []
        self.aws_lambda_permission = []
        self.aws_s3_bucket_notification = []
        self.aws_sqs_queue_policy = []
        self.aws_api_gateway_request_validator = []
        self.aws_lambda_layer_version = []

        self.compose_resources_mapping = {
            LAMBDA_RESOURCE_NAME: self._aws_lambda,
            IAM_POLICY_RESOURCE_NAME: self._aws_iam_policy,
            IAM_ROLE_RESOURCE_NAME: self._aws_iam_role,
            DYNAMO_DB_TABLE_RESOURCE_NAME: self._aws_dynamodb_table,
            APP_AUTOSCALING_TARGET_RESOURCE_NAME: self._aws_appautoscaling_target,
            APP_AUTOSCALING_POLICY_RESOURCE_NAME: self._aws_appautoscaling_policy,
            API_GATEWAY_REST_API_RESOURCE_NAME: self._aws_api_gateway_rest_api,
            API_GATEWAY_RESOURCE_RESOURCE_NAME: self._aws_api_gateway_resource,
            API_GATEWAY_METHOD_RESPONSE_RESOURCE_NAME: self._aws_api_gateway_method_response,
            API_GATEWAY_INTEGRATION_RESOURCE_NAME: self._aws_api_gateway_integration,
            API_GATEWAY_STAGE_RESOURCE_NAME: self._aws_api_gateway_stage,
            API_GATEWAY_DEPLOYMENT_RESOURCE_NAME: self._aws_api_gateway_deployment,
            API_GATEWAY_INTEGRATION_RESPONSE_RESOURCE_NAME: self._aws_api_gateway_integration_response,
            API_GATEWAY_METHOD_RESOURCE_NAME: self._aws_api_gateway_method,
            S3_BUCKET_RESOURCE_NAME: self._aws_aws_s3_bucket,
            CLOUD_WATCH_EVENT_RULE: self._aws_cloudwatch_event_rule,
            CLOUD_WATCH_EVENT_TARGET: self._aws_cloudwatch_event_target,
            SNS_TOPIC_RESOURCE: self._aws_sns_topic,
            SQS_QUEUE_RESOURCE: self._aws_sqs_queue,
            CLOUD_WATCH_ALARM: self._aws_cloudwatch_metric_alarm,
            KINESIS_STREAM_RESOURCE: self._aws_kinesis_stream,
            SNS_APPLICATION_RESOURCE: self._aws_sns_platform_application,
            AWS_API_GATEWAY_AUTHORIZER: self._aws_api_gateway_authorizer,
            AWS_COGNITO_IDENTITY_POOL: self._aws_cognito_identity_pool,
            AWS_COGNITO_IDENTITY_POOL_ROLES_ATTACHMENT: self._aws_cognito_identity_pool_roles_attachment,
            AWS_LAMBDA_PROVISIONED_CONCURRENCY_CONFIG: self._aws_lambda_provisioned_concurrency_config,
            AWS_LAMBDA_ALIAS: self._aws_lambda_alias,
            CLOUD_WATCH_LOG_GROUP: self._cloud_watch_log_group,
            SNS_TOPIC_POLICY: self._aws_sns_topic_policy,
            AWS_BATCH_JOB_DEFINITION: self._aws_batch_job_definition,
            AWS_BATCH_COMPUTE_ENVIRONMENT: self._aws_batch_compute_environment,
            AWS_BATCH_JOB_QUEUE: self._aws_batch_job_queue,
            AWS_IAM_INSTANCE_PROFILE: self._aws_iam_instance_profile,
            AWS_IAM_ROLE_POLICY_ATTACHMENT: self._aws_iam_role_policy_attachment,
            AWS_LAMBDA_EVENT_SOURCE_MAPPING: self._aws_lambda_event_source_mapping,
            AWS_IAM_ROLE_POLICY: self._aws_iam_role_policy,
            AWS_SNS_TOPIC_SUBSCRIPTION: self._aws_sns_topic_subscription,
            AWS_LAMBDA_PERMISSION: self._aws_lambda_permission,
            AWS_S3_BUCKET_NOTIFICATION: self._aws_s3_bucket_notification,
            AWS_SQS_POLICY: self._aws_sqs_queue_policy,
            AWS_API_GATEWAY_REQUEST_VALIDATOR: self._aws_api_gateway_request_validator,
            AWS_LAMBDA_LAYER_VERSION: self._aws_lambda_layer_version
        }

        self.provider = provider
        self.resources = list()
        self.providers = list()
        default_provider = {
            "profile": profile,
            "region": region
        }
        self.providers.append(default_provider)

    def add_aws_lambda(self, meta):
        self.aws_lambda_function.append(meta)

    def add_aws_iam_policy(self, meta):
        self.aws_iam_policy.append(meta)

    def add_aws_iam_role(self, meta):
        self.aws_iam_role.append(meta)

    def add_aws_dynamodb_table(self, meta):
        self.aws_dynamodb_table.append(meta)

    def add_aws_appautoscaling_target(self, meta):
        self.aws_appautoscaling_target.append(meta)

    def add_aws_appautoscaling_policy(self, meta):
        self.aws_appautoscaling_policy.append(meta)

    def add_aws_api_gateway_rest_api(self, meta):
        self.aws_api_gateway_rest_api.append(meta)

    def add_aws_api_gateway_resource(self, meta):
        self.aws_api_gateway_resource.append(meta)

    def add_aws_api_gateway_method_response(self, meta):
        self.aws_api_gateway_method_response.append(meta)

    def add_aws_api_gateway_integration(self, meta):
        self.aws_api_gateway_integration.append(meta)

    def add_aws_api_gateway_stage(self, meta):
        self.aws_api_gateway_stage.append(meta)

    def add_aws_api_gateway_deployment(self, meta):
        self.aws_api_gateway_deployment.append(meta)

    def add_aws_api_gateway_integration_response(self, meta):
        self.aws_api_gateway_integration_response.append(meta)

    def add_aws_api_gateway_method(self, meta):
        self.aws_api_gateway_method.append(meta)

    def add_aws_s3_bucket(self, meta):
        self.aws_s3_bucket.append(meta)

    def add_aws_cloudwatch_event_rule(self, meta):
        self.aws_cloudwatch_event_rule.append(meta)

    def add_aws_batch_job_definition(self, meta):
        self.aws_batch_job_definition.append(meta)

    def add_aws_cloudwatch_event_target(self, meta):
        self.aws_cloudwatch_event_target.append(meta)

    def add_aws_sns_topic(self, meta):
        self.aws_sns_topic.append(meta)

    def add_aws_sqs_queue(self, meta):
        self.aws_sqs_queue.append(meta)

    def add_aws_cloudwatch_metric_alarm(self, meta):
        self.aws_cloudwatch_metric_alarm.append(meta)

    def add_aws_kinesis_stream(self, meta):
        self.aws_kinesis_stream.append(meta)

    def add_aws_sns_platform_application(self, meta):
        self.aws_sns_platform_application.append(meta)

    def add_aws_api_gateway_authorizer(self, meta):
        self.aws_api_gateway_authorizer.append(meta)

    def add_aws_cognito_identity_pool(self, meta):
        self.aws_cognito_identity_pool.append(meta)

    def add_aws_cognito_identity_pool_roles_attachment(self, meta):
        self.aws_cognito_identity_pool_roles_attachment.append(meta)

    def add_aws_lambda_provisioned_concurrency_config(self, meta):
        self.aws_lambda_provisioned_concurrency_config.append(meta)

    def add_aws_lambda_alias(self, meta):
        self.aws_lambda_alias.append(meta)

    def add_cloud_watch_log_group(self, meta):
        self.cloud_watch_log_group.append(meta)

    def add_aws_sns_topic_policy(self, meta):
        self.aws_sns_topic_policy.append(meta)

    def add_aws_batch_job_queue(self, meta):
        self.aws_batch_job_queue.append(meta)

    def add_aws_batch_job_definition(self, meta):
        self.aws_batch_job_definition.append(meta)

    def add_aws_batch_compute_environment(self, meta):
        self.aws_batch_compute_environment.append(meta)

    def add_aws_iam_instance_profile(self, meta):
        self.aws_iam_instance_profile.append(meta)

    def add_aws_iam_role_policy_attachment(self, meta):
        self.aws_iam_role_policy_attachment.append(meta)

    def add_aws_lambda_event_source_mapping(self, meta):
        self.aws_lambda_event_source_mapping.append(meta)

    def add_aws_iam_role_policy(self, meta):
        self.aws_iam_role_policy.append(meta)

    def add_aws_sns_topic_subscription(self, meta):
        self.aws_sns_topic_subscription.append(meta)

    def add_aws_lambda_permission(self, meta):
        self.aws_lambda_permission.append(meta)

    def add_aws_s3_bucket_notification(self, meta):
        self.aws_s3_bucket_notification.append(meta)

    def add_aws_sqs_queue_policy(self, meta):
        self.aws_sqs_queue_policy.append(meta)

    def add_aws_api_gateway_request_validator(self, meta):
        self.aws_api_gateway_request_validator.append(meta)

    def add_aws_lambda_layer_version(self, meta):
        self.aws_lambda_layer_version.append(meta)

    def add_provider_if_not_exists(self, region):
        for provider in self.providers:
            if provider['region'] == region:
                return
        self.providers.append(
            {
                'region': region,
                'alias': region
            }
        )

    def _aws_lambda(self):
        return self.aws_lambda_function

    def _aws_iam_policy(self):
        return self.aws_iam_policy

    def _aws_iam_role(self):
        return self.aws_iam_role

    def _aws_dynamodb_table(self):
        return self.aws_dynamodb_table

    def _aws_appautoscaling_target(self):
        return self.aws_appautoscaling_target

    def _aws_appautoscaling_policy(self):
        return self.aws_appautoscaling_policy

    def _aws_api_gateway_rest_api(self):
        return self.aws_api_gateway_rest_api

    def _aws_api_gateway_resource(self):
        return self.aws_api_gateway_resource

    def _aws_api_gateway_method_response(self):
        return self.aws_api_gateway_method_response

    def _aws_api_gateway_integration(self):
        return self.aws_api_gateway_integration

    def _aws_api_gateway_stage(self):
        return self.aws_api_gateway_stage

    def _aws_api_gateway_deployment(self):
        return self.aws_api_gateway_deployment

    def _aws_api_gateway_integration_response(self):
        return self.aws_api_gateway_integration_response

    def _aws_api_gateway_method(self):
        return self.aws_api_gateway_method

    def _aws_aws_s3_bucket(self):
        return self.aws_s3_bucket

    def _aws_cloudwatch_event_rule(self):
        return self.aws_cloudwatch_event_rule

    def _aws_cloudwatch_event_target(self):
        return self.aws_cloudwatch_event_target

    def _aws_sns_topic(self):
        return self.aws_sns_topic

    def _aws_sqs_queue(self):
        return self.aws_sqs_queue

    def _aws_cloudwatch_metric_alarm(self):
        return self.aws_cloudwatch_metric_alarm

    def _aws_kinesis_stream(self):
        return self.aws_kinesis_stream

    def _aws_sns_platform_application(self):
        return self.aws_sns_platform_application

    def _aws_api_gateway_authorizer(self):
        return self.aws_api_gateway_authorizer

    def _aws_cognito_identity_pool(self):
        return self.aws_cognito_identity_pool

    def _aws_cognito_identity_pool_roles_attachment(self):
        return self.aws_cognito_identity_pool_roles_attachment

    def _aws_lambda_provisioned_concurrency_config(self):
        return self.aws_lambda_provisioned_concurrency_config

    def _aws_lambda_alias(self):
        return self.aws_lambda_alias

    def _cloud_watch_log_group(self):
        return self.cloud_watch_log_group

    def _aws_sns_topic_policy(self):
        return self.aws_sns_topic_policy

    def _aws_batch_job_definition(self):
        return self.aws_batch_job_definition

    def _aws_batch_compute_environment(self):
        return self.aws_batch_compute_environment

    def _aws_batch_job_queue(self):
        return self.aws_batch_job_queue

    def _aws_iam_instance_profile(self):
        return self.aws_iam_instance_profile

    def _aws_iam_role_policy_attachment(self):
        return self.aws_iam_role_policy_attachment

    def _aws_lambda_event_source_mapping(self):
        return self.aws_lambda_event_source_mapping

    def _aws_iam_role_policy(self):
        return self.aws_iam_role_policy

    def _aws_sns_topic_subscription(self):
        return self.aws_sns_topic_subscription

    def _aws_lambda_permission(self):
        return self.aws_lambda_permission

    def _aws_s3_bucket_notification(self):
        return self.aws_s3_bucket_notification

    def _aws_sqs_queue_policy(self):
        return self.aws_sqs_queue_policy

    def _aws_api_gateway_request_validator(self):
        return self.aws_api_gateway_request_validator

    def _aws_lambda_layer_version(self):
        return self.aws_lambda_layer_version

    def provider_type(self):
        return self.provider

    def get_resource_by_name(self, resource_name):
        for res_type in RESOURCE_TYPES:
            resource_extractor = self.compose_resources_mapping.get(res_type)
            resources_meta = resource_extractor()
            if resources_meta:
                for resource in resources_meta:
                    if resource.get(resource_name):
                        return resource.get(resource_name)

    def compose_resources(self):
        for res_type in RESOURCE_TYPES:
            resource_extractor = self.compose_resources_mapping.get(res_type)
            resources_meta = resource_extractor()
            if resources_meta:
                self.resources.append({res_type: resources_meta})
        return json.dumps({PROVIDER_KEY: {self.provider: self.providers},
                           RESOURCE_KEY: self.resources}, indent=2)
