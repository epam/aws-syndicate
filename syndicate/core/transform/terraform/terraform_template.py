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
                  AWS_COGNITO_IDENTITY_POOL_ROLES_ATTACHMENT]


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
            AWS_COGNITO_IDENTITY_POOL_ROLES_ATTACHMENT: self._aws_cognito_identity_pool_roles_attachment
        }

        self.resources = list()
        self.provider = list()
        provider_config = {
            provider: [
                {
                    "profile": profile,
                    "region": region
                }
            ]
        }
        self.provider.append(provider_config)

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

    def add_dynamo_db_stream(self, table_name, view_type):
        for table in self.aws_dynamodb_table:
            for resource in table.values():
                if table_name == resource.get('name'):
                    resource.update({'stream_enabled': 'true'})
                    resource.update({'stream_view_type': view_type})

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

    def compose_resources(self):
        for res_type in RESOURCE_TYPES:
            resource_extractor = self.compose_resources_mapping.get(res_type)
            resources_meta = resource_extractor()
            if resources_meta:
                self.resources.append({res_type: resources_meta})
        return json.dumps({PROVIDER_KEY: self.provider,
                           RESOURCE_KEY: self.resources})
