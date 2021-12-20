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
COGNITO_FEDERATED_POOL_TYPE = 'cognito_federated_pool'
COGNITO_USER_POOL_TYPE = 'cognito_idp'
SNS_TOPIC_TYPE = 'sns_topic'
SNS_PLATFORM_APPLICATION_TYPE = 'sns_application'
CLOUD_WATCH_ALARM_TYPE = 'cloudwatch_alarm'
EBS_TYPE = 'beanstalk_app'
STEP_FUNCTION_TYPE = 'step_functions'
KINESIS_STREAM_TYPE = 'kinesis_stream'
STATE_ACTIVITY_TYPE = 'state_activity'
EC2_INSTANCE_TYPE = 'ec2_instance'
BATCH_COMPENV_TYPE = 'batch_compenv'
BATCH_JOBQUEUE_TYPE = 'batch_jobqueue'
BATCH_JOBDEF_TYPE = 'batch_jobdef'
DOCUMENTDB_CLUSTER_TYPE = 'documentdb_cluster'
DOCUMENTDB_INSTANCE_TYPE = 'documentdb_instance'

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
    COGNITO_USER_POOL_TYPE: 15,
    API_GATEWAY_TYPE: 16,
    COGNITO_FEDERATED_POOL_TYPE: 17,
    EBS_TYPE: 18,
    EC2_INSTANCE_TYPE: 19,
    SNS_PLATFORM_APPLICATION_TYPE: 20,
    BATCH_COMPENV_TYPE: 21,
    BATCH_JOBQUEUE_TYPE: 22,
    BATCH_JOBDEF_TYPE: 23,
    DOCUMENTDB_CLUSTER_TYPE: 24,
    DOCUMENTDB_INSTANCE_TYPE: 25
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
    COGNITO_USER_POOL_TYPE: 15,
    API_GATEWAY_TYPE: 16,
    COGNITO_FEDERATED_POOL_TYPE: 17,
    EBS_TYPE: 18,
    EC2_INSTANCE_TYPE: 19,
    SNS_PLATFORM_APPLICATION_TYPE: 20,
    BATCH_JOBDEF_TYPE: 21,
    BATCH_JOBQUEUE_TYPE: 22,
    BATCH_COMPENV_TYPE: 23,
    DOCUMENTDB_CLUSTER_TYPE: 24,
    DOCUMENTDB_INSTANCE_TYPE: 25
}

UPDATE_RESOURCE_TYPE_PRIORITY = {
    IAM_POLICY: 1,
    IAM_ROLE: 2,
    LAMBDA_LAYER_TYPE: 3,
    LAMBDA_TYPE: 4,    
    BATCH_JOBDEF_TYPE: 6,
    BATCH_COMPENV_TYPE: 5
}

RESOURCE_LIST = list(DEPLOY_RESOURCE_TYPE_PRIORITY.keys())
DATE_FORMAT_ISO_8601 = '%Y-%m-%dT%H:%M:%SZ'
