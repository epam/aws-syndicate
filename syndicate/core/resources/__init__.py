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
from syndicate.core import CONFIG, CREDENTIALS
from syndicate.core.constants import (API_GATEWAY_TYPE, CLOUD_WATCH_ALARM_TYPE,
                                      CLOUD_WATCH_RULE_TYPE, COGNITO_TYPE,
                                      DYNAMO_TABLE_TYPE, EBS_TYPE,
                                      EC2_INSTANCE_TYPE, IAM_POLICY,
                                      IAM_ROLE, KINESIS_STREAM_TYPE,
                                      LAMBDA_TYPE, S3_BUCKET_TYPE,
                                      SNS_PLATFORM_APPLICATION_TYPE,
                                      SNS_TOPIC_TYPE,
                                      SQS_QUEUE_TYPE, STATE_ACTIVITY_TYPE,
                                      STEP_FUNCTION_TYPE, LAMBDA_LAYER_TYPE)
from syndicate.core.resources._resources_provider import ResourceProvider

RESOURCES_PROVIDER = ResourceProvider(config=CONFIG,
                                      credentials=CREDENTIALS)

CREATE_RESOURCE = {
    IAM_POLICY:
        RESOURCES_PROVIDER.iam().create_policies,
    IAM_ROLE:
        RESOURCES_PROVIDER.iam().create_roles,
    LAMBDA_TYPE:
        RESOURCES_PROVIDER.lambda_resource().create_lambda,
    LAMBDA_LAYER_TYPE:
        RESOURCES_PROVIDER.lambda_resource().create_lambda_layer,
    DYNAMO_TABLE_TYPE:
        RESOURCES_PROVIDER.dynamodb().create_tables_by_10,
    CLOUD_WATCH_RULE_TYPE:
        RESOURCES_PROVIDER.cw_resource().create_cloud_watch_rule,
    S3_BUCKET_TYPE:
        RESOURCES_PROVIDER.s3().create_s3_bucket,
    API_GATEWAY_TYPE:
        RESOURCES_PROVIDER.api_gw().create_api_gateway,
    COGNITO_TYPE:
        RESOURCES_PROVIDER.cognito().create_cognito_identity_pool,
    SNS_TOPIC_TYPE:
        RESOURCES_PROVIDER.sns().create_sns_topic,
    SNS_PLATFORM_APPLICATION_TYPE:
        RESOURCES_PROVIDER.sns().create_sns_application,
    SQS_QUEUE_TYPE:
        RESOURCES_PROVIDER.sqs().create_sqs_queue,
    CLOUD_WATCH_ALARM_TYPE:
        RESOURCES_PROVIDER.cw().create_alarm,
    EBS_TYPE:
        RESOURCES_PROVIDER.ebs().create_ebs,
    STEP_FUNCTION_TYPE:
        RESOURCES_PROVIDER.step_functions().create_state_machine,
    STATE_ACTIVITY_TYPE:
        RESOURCES_PROVIDER.step_functions().create_activities,
    KINESIS_STREAM_TYPE:
        RESOURCES_PROVIDER.kinesis().create_kinesis_stream,
    EC2_INSTANCE_TYPE:
        RESOURCES_PROVIDER.ec2().create_ec2
}

# 'ec2_instance' type is not supported
DESCRIBE_RESOURCE = {
    IAM_POLICY:
        RESOURCES_PROVIDER.iam().describe_policy,
    IAM_ROLE:
        RESOURCES_PROVIDER.iam().describe_role,
    LAMBDA_TYPE:
        RESOURCES_PROVIDER.lambda_resource().describe_lambda,
    DYNAMO_TABLE_TYPE:
        RESOURCES_PROVIDER.dynamodb().describe_table,
    CLOUD_WATCH_RULE_TYPE:
        RESOURCES_PROVIDER.cw_resource().describe_rule_from_meta,
    S3_BUCKET_TYPE:
        RESOURCES_PROVIDER.s3().describe_bucket,
    API_GATEWAY_TYPE:
        RESOURCES_PROVIDER.api_gw().describe_api_resources,
    COGNITO_TYPE:
        RESOURCES_PROVIDER.cognito().describe_cognito_pool,
    SNS_TOPIC_TYPE:
        RESOURCES_PROVIDER.sns().describe_sns_from_meta,
    SNS_PLATFORM_APPLICATION_TYPE:
        RESOURCES_PROVIDER.sns().describe_sns_application_from_meta,
    SQS_QUEUE_TYPE:
        RESOURCES_PROVIDER.sqs().describe_queue_from_meta,
    CLOUD_WATCH_ALARM_TYPE:
        RESOURCES_PROVIDER.cw().describe_alarm,
    EBS_TYPE:
        RESOURCES_PROVIDER.ebs().describe_ebs,
    STEP_FUNCTION_TYPE:
        RESOURCES_PROVIDER.step_functions().describe_step_function,
    STATE_ACTIVITY_TYPE:
        RESOURCES_PROVIDER.step_functions().describe_activity,
    KINESIS_STREAM_TYPE:
        RESOURCES_PROVIDER.kinesis().describe_kinesis_stream,
}

REMOVE_RESOURCE = {
    CLOUD_WATCH_ALARM_TYPE:
        RESOURCES_PROVIDER.cw().remove_alarms,
    API_GATEWAY_TYPE:
        RESOURCES_PROVIDER.api_gw().remove_api_gateways,
    CLOUD_WATCH_RULE_TYPE:
        RESOURCES_PROVIDER.cw_resource().remove_cloud_watch_rules,
    COGNITO_TYPE:
        RESOURCES_PROVIDER.cognito().remove_cognito_identity_pools,
    DYNAMO_TABLE_TYPE:
        RESOURCES_PROVIDER.dynamodb().remove_dynamodb_tables,
    EBS_TYPE:
        RESOURCES_PROVIDER.ebs().remove_ebs_apps,
    EC2_INSTANCE_TYPE:
        RESOURCES_PROVIDER.ec2().remove_ec2_instances,
    IAM_ROLE:
        RESOURCES_PROVIDER.iam().remove_roles,
    IAM_POLICY:
        RESOURCES_PROVIDER.iam().remove_policies,
    KINESIS_STREAM_TYPE:
        RESOURCES_PROVIDER.kinesis().remove_kinesis_streams,
    LAMBDA_LAYER_TYPE:
        RESOURCES_PROVIDER.lambda_resource().remove_lambda_layers,
    LAMBDA_TYPE:
        RESOURCES_PROVIDER.lambda_resource().remove_lambdas,
    S3_BUCKET_TYPE:
        RESOURCES_PROVIDER.s3().remove_buckets,
    SNS_TOPIC_TYPE:
        RESOURCES_PROVIDER.sns().remove_sns_topics,
    SNS_PLATFORM_APPLICATION_TYPE:
        RESOURCES_PROVIDER.sns().remove_sns_application,
    SQS_QUEUE_TYPE:
        RESOURCES_PROVIDER.sqs().remove_queues,
    STEP_FUNCTION_TYPE:
        RESOURCES_PROVIDER.step_functions().remove_state_machines,
    STATE_ACTIVITY_TYPE:
        RESOURCES_PROVIDER.step_functions().remove_activities
}

UPDATE_RESOURCE = {
    LAMBDA_TYPE: RESOURCES_PROVIDER.lambda_resource().update_lambda,
    LAMBDA_LAYER_TYPE: RESOURCES_PROVIDER.lambda_resource().update_lambda_layer
}

RESOURCE_CONFIGURATION_PROCESSORS = {
    API_GATEWAY_TYPE: RESOURCES_PROVIDER.api_gw().api_gateway_update_processor
}

RESOURCE_IDENTIFIER = {
    API_GATEWAY_TYPE: RESOURCES_PROVIDER.api_gw().api_resource_identifier,
    COGNITO_TYPE: RESOURCES_PROVIDER.cognito().cognito_resource_identifier
}

APPLY_MAPPING = {
    IAM_ROLE: RESOURCES_PROVIDER.iam().apply_trusted_to_role,
    IAM_POLICY: RESOURCES_PROVIDER.iam().apply_policy_content
}
