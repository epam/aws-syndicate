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
DAX_CLUSTER_TYPE = 'dax_cluster'
S3_BUCKET_TYPE = 's3_bucket'
CLOUD_WATCH_RULE_TYPE = 'cloudwatch_rule'
EVENT_BRIDGE_RULE_TYPE = 'eventbridge_rule'
EVENT_BRIDGE_SCHEDULE_TYPE = 'eventbridge_schedule'
SQS_QUEUE_TYPE = 'sqs_queue'
API_GATEWAY_TYPE = 'api_gateway'
API_GATEWAY_OAS_V3_TYPE = 'api_gateway_oas_v3'
WEB_SOCKET_API_GATEWAY_TYPE = 'web_socket_api_gateway'
SWAGGER_UI_TYPE = 'swagger_ui'
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
EC2_LAUNCH_TEMPLATE_TYPE = 'ec2_launch_template'
BATCH_COMPENV_TYPE = 'batch_compenv'
BATCH_JOBQUEUE_TYPE = 'batch_jobqueue'
BATCH_JOBDEF_TYPE = 'batch_jobdef'
FIREHOSE_TYPE = 'firehose'
DOCUMENTDB_CLUSTER_TYPE = 'documentdb_cluster'
DOCUMENTDB_INSTANCE_TYPE = 'documentdb_instance'

S3_PATH_NAME = 's3_path'
EXPORT_DIR_NAME = 'export'

# == BUILD PARAMS =============================================================
ARTIFACTS_FOLDER = 'bundles'
BUILD_META_FILE_NAME = 'build_meta.json'
LAMBDA_CONFIG_FILE_NAME = 'lambda_config.json'
LAMBDA_LAYER_CONFIG_FILE_NAME = 'lambda_layer_config.json'
REQ_FILE_NAME = 'requirements.txt'
NODE_REQ_FILE_NAME = 'package.json'
LOCAL_REQ_FILE_NAME = 'local_requirements.txt'
RESOURCES_FILE_NAME = 'deployment_resources.json'
OAS_V3_FILE_NAME = 'oas_v3.json'
SWAGGER_UI_SPEC_NAME_TEMPLATE = '{name}_spec.json'
SWAGGER_UI_ARTIFACT_NAME_TEMPLATE = 'swagger_ui_{name}.zip'
SWAGGER_UI_CONFIG_FILE_NAME = 'swagger_ui_config.json'
# layer.zip
# │ python/PIL
# └ python/Pillow-5.3.0.dist-info
PYTHON_LAMBDA_LAYER_PATH = 'python'
NODE_LAMBDA_LAYER_PATH = 'nodejs'

DEFAULT_SEP = '/'

DEPLOY_RESOURCE_TYPE_PRIORITY = {
    IAM_POLICY: 1,
    IAM_ROLE: 2,
    DYNAMO_TABLE_TYPE: 3,
    DAX_CLUSTER_TYPE: 4,
    S3_BUCKET_TYPE: 5,
    CLOUD_WATCH_RULE_TYPE: 6,
    EVENT_BRIDGE_RULE_TYPE: 6,
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
    API_GATEWAY_OAS_V3_TYPE: 17,
    WEB_SOCKET_API_GATEWAY_TYPE: 18,
    SWAGGER_UI_TYPE: 19,
    COGNITO_FEDERATED_POOL_TYPE: 19,
    EC2_LAUNCH_TEMPLATE_TYPE: 19,
    EBS_TYPE: 20,
    EC2_INSTANCE_TYPE: 21,
    SNS_PLATFORM_APPLICATION_TYPE: 22,
    BATCH_COMPENV_TYPE: 23,
    BATCH_JOBQUEUE_TYPE: 24,
    BATCH_JOBDEF_TYPE: 25,
    FIREHOSE_TYPE: 26,
    DOCUMENTDB_CLUSTER_TYPE: 27,
    DOCUMENTDB_INSTANCE_TYPE: 28,
    EVENT_BRIDGE_SCHEDULE_TYPE: 29
}

CLEAN_RESOURCE_TYPE_PRIORITY = {
    IAM_ROLE: 1,
    IAM_POLICY: 2,
    DAX_CLUSTER_TYPE: 3,
    DYNAMO_TABLE_TYPE: 4,
    SWAGGER_UI_TYPE: 4,
    S3_BUCKET_TYPE: 5,
    CLOUD_WATCH_RULE_TYPE: 6,
    EVENT_BRIDGE_RULE_TYPE: 6,
    SNS_TOPIC_TYPE: 7,
    SQS_QUEUE_TYPE: 8,
    KINESIS_STREAM_TYPE: 9,
    CLOUD_WATCH_ALARM_TYPE: 10,
    LAMBDA_TYPE: 11,
    LAMBDA_LAYER_TYPE: 12,
    STATE_ACTIVITY_TYPE: 13,
    STEP_FUNCTION_TYPE: 14,
    COGNITO_USER_POOL_TYPE: 15,
    WEB_SOCKET_API_GATEWAY_TYPE: 16,
    API_GATEWAY_TYPE: 17,
    API_GATEWAY_OAS_V3_TYPE: 18,
    COGNITO_FEDERATED_POOL_TYPE: 19,
    EBS_TYPE: 20,
    EC2_INSTANCE_TYPE: 21,
    SNS_PLATFORM_APPLICATION_TYPE: 22,
    BATCH_JOBDEF_TYPE: 23,
    BATCH_JOBQUEUE_TYPE: 24,
    BATCH_COMPENV_TYPE: 25,
    EC2_LAUNCH_TEMPLATE_TYPE: 25,
    FIREHOSE_TYPE: 26,
    DOCUMENTDB_INSTANCE_TYPE: 27,
    DOCUMENTDB_CLUSTER_TYPE: 28,
    EVENT_BRIDGE_SCHEDULE_TYPE: 29
}

UPDATE_RESOURCE_TYPE_PRIORITY = {
    IAM_POLICY: 1,
    IAM_ROLE: 2,
    DYNAMO_TABLE_TYPE: 3,
    LAMBDA_LAYER_TYPE: 4,
    LAMBDA_TYPE: 5,
    API_GATEWAY_OAS_V3_TYPE: 6,
    EC2_LAUNCH_TEMPLATE_TYPE: 6,
    BATCH_JOBDEF_TYPE: 7,
    BATCH_COMPENV_TYPE: 8,
    SWAGGER_UI_TYPE: 9
}

RESOURCE_LIST = list(DEPLOY_RESOURCE_TYPE_PRIORITY.keys())
DATE_FORMAT_ISO_8601 = '%Y-%m-%dT%H:%M:%SZ'

TEST_ACTION = 'test'
BUILD_ACTION = 'build'
DEPLOY_ACTION = 'deploy'
UPDATE_ACTION = 'update'
CLEAN_ACTION = 'clean'
PARTIAL_CLEAN_ACTION = 'partial_clean'
SYNC_ACTION = 'sync'
STATUS_ACTION = 'status'
WARMUP_ACTION = 'warmup'
PROFILER_ACTION = 'profiler'
ASSEMBLE_JAVA_MVN_ACTION = 'assemble_java_mvn'
ASSEMBLE_PYTHON_ACTION = 'assemble_python'
ASSEMBLE_NODE_ACTION = 'assemble_node'
ASSEMBLE_SWAGGER_UI_ACTION = 'assemble_swagger_ui'
ASSEMBLE_ACTION = 'assemble'
PACKAGE_META_ACTION = 'package_meta'
CREATE_DEPLOY_TARGET_BUCKET_ACTION = 'create_deploy_target_bucket'
UPLOAD_ACTION = 'upload'
COPY_BUNDLE_ACTION = 'copy_bundle'
EXPORT_ACTION = 'export'

NONE_AUTH_TYPE, IAM_AUTH_TYPE = 'NONE', 'AWS_IAM'

MANY_LINUX_2014_PLATFORM = 'manylinux2014_x86_64'
OPTIMAL_INSTANCE_TYPE = 'optimal'

POSSIBLE_RETENTION_DAYS = (
1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192,
2557, 2922, 3288, 3653)
DEFAULT_LOGS_EXPIRATION = 30
SOURCE_ARN_DEEP_KEY = ('Condition', 'ArnLike', 'AWS:SourceArn')
SECURITY_SCHEMAS_DEEP_KEY = ('components', 'securitySchemes')
LAMBDA_ARCHITECTURE_LIST = ['x86_64', 'arm64']

API_GW_DEFAULT_THROTTLING_RATE_LIMIT = 10000
API_GW_DEFAULT_THROTTLING_BURST_LIMIT = 5000
COGNITO_USER_POOL_AUTHORIZER_TYPE = 'COGNITO_USER_POOLS'
REQUEST_LAMBDA_AUTHORIZER_TYPE = 'REQUEST'
TOKEN_LAMBDA_AUTHORIZER_TYPE = 'TOKEN'
API_GW_AUTHORIZER_TYPES = [COGNITO_USER_POOL_AUTHORIZER_TYPE,
                           TOKEN_LAMBDA_AUTHORIZER_TYPE,
                           REQUEST_LAMBDA_AUTHORIZER_TYPE]
CUSTOM_AUTHORIZER_KEY = 'CUSTOM'

S3_BUCKET_ACL_LIST = ['private', 'public-read',
                      'public-read-write', 'authenticated-read']


SYNDICATE_WIKI_PAGE = 'https://github.com/epam/aws-syndicate/wiki/'
SYNDICATE_PROJECT_EXAMPLES_PAGE = 'https://github.com/epam/aws-syndicate/tree/master/examples/'

JAVA_LAMBDAS_WIKI_PAGE = '3.-Lambda-Requirements-for-Automatic-Articfacts-Build#32-java-lambdas'

EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS = ['v1.0', 'v2.0']
