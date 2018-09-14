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
from core.constants import (API_GATEWAY_TYPE, CLOUD_WATCH_ALARM_TYPE,
                            CLOUD_WATCH_RULE_TYPE, COGNITO_TYPE,
                            DYNAMO_STREAM_TYPE, DYNAMO_TABLE_TYPE, EBS_TYPE,
                            EC2_INSTANCE_TYPE, IAM_POLICY, IAM_ROLE,
                            KINESIS_STREAM_TYPE,
                            LAMBDA_TYPE, S3_BUCKET_TYPE,
                            SNS_PLATFORM_APPLICATION_TYPE, SNS_TOPIC_TYPE,
                            SQS_QUEUE_TYPE, STATE_ACTIVITY_TYPE,
                            STEP_FUNCTION_TYPE)
from core.resources.alarm_resource import create_alarm, remove_alarms
from core.resources.api_gateway_resource import (api_resource_identifier,
                                                 create_api_gateway,
                                                 remove_api_gateways)
from core.resources.cloud_watch_resource import (create_cloud_watch_rule,
                                                 remove_cloud_watch_rules)
from core.resources.cognito_resource import (cognito_resource_identifier,
                                             create_cognito_identity_pool,
                                             remove_cognito_identity_pools)
from core.resources.dynamo_db_resource import (create_dynamodb_stream,
                                               create_tables_by_10,
                                               remove_dynamodb_tables)
from core.resources.ebs_resource import create_ebs, remove_ebs_apps
from core.resources.ec2_resource import create_ec2, remove_ec2_instances
from core.resources.iam_resource import (apply_policy_content,
                                         apply_trusted_to_role,
                                         create_policies, create_roles,
                                         remove_policies,
                                         remove_roles)
from core.resources.kinesis_resource import (create_kinesis_stream,
                                             remove_kinesis_streams)
from core.resources.lambda_resource import create_lambda, remove_lambdas
from core.resources.s3_resource import create_s3_bucket, remove_buckets
from core.resources.sns_resource import (create_sns_application,
                                         create_sns_topic,
                                         remove_sns_application,
                                         remove_sns_topics)
from core.resources.sqs_resource import create_sqs_queue, remove_queues
from core.resources.step_functions_resource import (create_activities,
                                                    create_state_machine,
                                                    remove_activities,
                                                    remove_state_machines)

CREATE_RESOURCE = {
    IAM_POLICY: create_policies,
    IAM_ROLE: create_roles,
    LAMBDA_TYPE: create_lambda,
    DYNAMO_TABLE_TYPE: create_tables_by_10,
    DYNAMO_STREAM_TYPE: create_dynamodb_stream,
    CLOUD_WATCH_RULE_TYPE: create_cloud_watch_rule,
    S3_BUCKET_TYPE: create_s3_bucket,
    API_GATEWAY_TYPE: create_api_gateway,
    COGNITO_TYPE: create_cognito_identity_pool,
    SNS_TOPIC_TYPE: create_sns_topic,
    SNS_PLATFORM_APPLICATION_TYPE: create_sns_application,
    SQS_QUEUE_TYPE: create_sqs_queue,
    CLOUD_WATCH_ALARM_TYPE: create_alarm,
    EBS_TYPE: create_ebs,
    STEP_FUNCTION_TYPE: create_state_machine,
    STATE_ACTIVITY_TYPE: create_activities,
    KINESIS_STREAM_TYPE: create_kinesis_stream,
    EC2_INSTANCE_TYPE: create_ec2
}

REMOVE_RESOURCE = {
    CLOUD_WATCH_ALARM_TYPE: remove_alarms,
    API_GATEWAY_TYPE: remove_api_gateways,
    CLOUD_WATCH_RULE_TYPE: remove_cloud_watch_rules,
    COGNITO_TYPE: remove_cognito_identity_pools,
    DYNAMO_TABLE_TYPE: remove_dynamodb_tables,
    EBS_TYPE: remove_ebs_apps,
    EC2_INSTANCE_TYPE: remove_ec2_instances,
    IAM_ROLE: remove_roles,
    IAM_POLICY: remove_policies,
    KINESIS_STREAM_TYPE: remove_kinesis_streams,
    LAMBDA_TYPE: remove_lambdas,
    S3_BUCKET_TYPE: remove_buckets,
    SNS_TOPIC_TYPE: remove_sns_topics,
    SNS_PLATFORM_APPLICATION_TYPE: remove_sns_application,
    SQS_QUEUE_TYPE: remove_queues,
    STEP_FUNCTION_TYPE: remove_state_machines,
    STATE_ACTIVITY_TYPE: remove_activities
}

RESOURCE_IDENTIFIER = {
    API_GATEWAY_TYPE: api_resource_identifier,
    COGNITO_TYPE: cognito_resource_identifier
}

APPLY_MAPPING = {
    IAM_ROLE: apply_trusted_to_role,
    IAM_POLICY: apply_policy_content
}
