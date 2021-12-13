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
        import DynamoDBGenerator, DynamoDBGlobalIndexGenerator
from syndicate.core.generators.deployment_resources.s3_generator \
        import S3Generator
from syndicate.core.generators.deployment_resources.api_gateway_generator \
        import ApiGatewayGenerator, ApiGatewayResourceGenerator
from syndicate.core.generators.deployment_resources.iam_policy_generator \
        import IAMPolicyGenerator
from syndicate.core.generators.deployment_resources.iam_role_generator \
        import IAMRoleGenerator
from syndicate.core.generators.deployment_resources.kinesis_stream_generator \
        import KinesisStreamGenerator
from syndicate.core.generators.deployment_resources.sns_topic_generator \
        import SNSTopicGenerator
from syndicate.core.generators.deployment_resources.\
        step_function_activity_generator import StepFunctionActivityGenerator
from syndicate.core.generators.deployment_resources.base_generator import \
        BaseConfigurationGenerator
