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
IAM_POLICY = 'iam_policy'
IAM_ROLE = 'iam_role'
LAMBDA_TYPE = 'lambda'
LAMBDA_LAYER_TYPE = 'lambda_layer'
DYNAMO_TABLE_TYPE = 'dynamodb_table'
S3_BUCKET_TYPE = 's3_bucket'
CLOUD_WATCH_RULE_TYPE = 'cloudwatch_rule'
SQS_QUEUE_TYPE = 'sqs_queue'
API_GATEWAY_TYPE = 'api_gateway'
COGNITO_TYPE = 'cognito_federated_pool'
SNS_TOPIC_TYPE = 'sns_topic'
SNS_PLATFORM_APPLICATION_TYPE = 'sns_application'
CLOUD_WATCH_ALARM_TYPE = 'cloudwatch_alarm'
EBS_TYPE = 'beanstalk_app'
STEP_FUNCTION_TYPE = 'step_functions'
KINESIS_STREAM_TYPE = 'kinesis_stream'
STATE_ACTIVITY_TYPE = 'state_activity'
EC2_INSTANCE_TYPE = 'ec2_instance'

S3_PATH_NAME = 's3_path'

# == BUILD PARAMS =============================================================
ARTIFACTS_FOLDER = 'bundles'
BUILD_META_FILE_NAME = 'build_meta.json'
LAMBDA_CONFIG_FILE_NAME = 'lambda_config.json'
REQ_FILE_NAME = 'requirements.txt'
NODE_REQ_FILE_NAME = 'package.json'
LOCAL_REQ_FILE_NAME = 'local_requirements.txt'
RESOURCES_FILE_NAME = 'deployment_resources.json'

DEFAULT_SEP = '/'

DEPLOY_RESOURCE_TYPE_PRIORITY = {
    IAM_POLICY: 1,
    IAM_ROLE: 2,
    DYNAMO_TABLE_TYPE: 3,
    S3_BUCKET_TYPE: 4,
    CLOUD_WATCH_RULE_TYPE: 5,
    SNS_TOPIC_TYPE: 7,
    SQS_QUEUE_TYPE: 8,
    KINESIS_STREAM_TYPE: 9,
    CLOUD_WATCH_ALARM_TYPE: 10,
    LAMBDA_LAYER_TYPE: 11,
    LAMBDA_TYPE: 12,
    STATE_ACTIVITY_TYPE: 13,
    STEP_FUNCTION_TYPE: 14,
    API_GATEWAY_TYPE: 15,
    COGNITO_TYPE: 16,
    EBS_TYPE: 17,
    EC2_INSTANCE_TYPE: 18,
    SNS_PLATFORM_APPLICATION_TYPE: 19
}

CLEAN_RESOURCE_TYPE_PRIORITY = {
    IAM_POLICY: 2,
    IAM_ROLE: 1,
    DYNAMO_TABLE_TYPE: 3,
    S3_BUCKET_TYPE: 4,
    CLOUD_WATCH_RULE_TYPE: 5,
    SNS_TOPIC_TYPE: 7,
    SQS_QUEUE_TYPE: 8,
    KINESIS_STREAM_TYPE: 9,
    CLOUD_WATCH_ALARM_TYPE: 10,
    LAMBDA_TYPE: 11,
    LAMBDA_LAYER_TYPE: 12,
    STATE_ACTIVITY_TYPE: 13,
    STEP_FUNCTION_TYPE: 14,
    API_GATEWAY_TYPE: 15,
    COGNITO_TYPE: 16,
    EBS_TYPE: 17,
    EC2_INSTANCE_TYPE: 18,
    SNS_PLATFORM_APPLICATION_TYPE: 19
}

UPDATE_RESOURCE_TYPE_PRIORITY = {
    LAMBDA_LAYER_TYPE: 1,
    LAMBDA_TYPE: 2
}

RESOURCE_LIST = list(DEPLOY_RESOURCE_TYPE_PRIORITY.keys())
