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
from syndicate.core.generators.deployment_resources.dynamodb_generator \
    import DynamoDBGenerator, DynamoDBGlobalIndexGenerator, \
    DynamoDBAutoscalingGenerator
from syndicate.core.generators.deployment_resources.s3_bucket_generator \
    import S3Generator
from syndicate.core.generators.deployment_resources.api_gateway_generator \
    import ApiGatewayGenerator, ApiGatewayResourceGenerator, \
    ApiGatewayResourceMethodGenerator
from syndicate.core.generators.deployment_resources.iam_policy_generator \
    import IAMPolicyGenerator
from syndicate.core.generators.deployment_resources.iam_role_generator \
    import IAMRoleGenerator
from syndicate.core.generators.deployment_resources.kinesis_stream_generator \
    import KinesisStreamGenerator
from syndicate.core.generators.deployment_resources.sns_topic_generator \
    import SNSTopicGenerator
from syndicate.core.generators.deployment_resources. \
    step_function_activity_generator import StepFunctionActivityGenerator
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseConfigurationGenerator
from syndicate.core.generators.deployment_resources.ec2_instance_generator \
    import EC2InstanceGenerator
from syndicate.core.generators.deployment_resources.sqs_queue_generator \
    import SQSQueueGenerator
from syndicate.core.generators.deployment_resources.sns_application_generator \
    import SNSApplicationGenerator
from syndicate.core.generators.deployment_resources. \
    cognito_user_pool_generator import CognitoUserPoolGenerator
from syndicate.core.generators.deployment_resources. \
    batch_compenv_generator import BatchCompenvGenerator
from syndicate.core.generators.deployment_resources.batch_jobqueue_generator \
    import BatchJobqueueGenerator
from syndicate.core.generators.deployment_resources.batch_jobdef_generator \
    import BatchJobdefGenerator
from syndicate.core.generators.deployment_resources. \
    cloudwatch_alarm_generator import CloudWatchAlarmGenerator
from syndicate.core.generators.deployment_resources.step_function_generator \
    import StepFunctionGenerator
from syndicate.core.generators.deployment_resources.cognito_federated_generator \
    import CognitoFederatedPoolGenerator
from syndicate.core.generators.deployment_resources. \
    cloudwatch_event_rule_generator import CloudwatchEventRuleGenerator
from syndicate.core.generators.deployment_resources.docdb_cluster_generator \
    import DocumentDBClusterGenerator
from syndicate.core.generators.deployment_resources.docdb_instance_generator \
    import DocumentDBInstanceGenerator
from syndicate.core.generators.deployment_resources.dax_cluster_generator \
    import DaxClusterGenerator
from syndicate.core.generators.deployment_resources.eventbridge_rule_generator \
    import EventBridgeRuleGenerator
from syndicate.core.generators.deployment_resources.\
    web_socket_api_gateway_generator import WebSocketApiGatewayGenerator
