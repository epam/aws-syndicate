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


class ProcessorFacade:

    def __init__(self, resources_provider) -> None:
        self.resources_provider = resources_provider

    def create_handlers(self):
        return {
            IAM_POLICY:
                self.resources_provider.iam().create_policies,
            IAM_ROLE:
                self.resources_provider.iam().create_roles,
            LAMBDA_TYPE:
                self.resources_provider.lambda_resource().create_lambda,
            LAMBDA_LAYER_TYPE:
                self.resources_provider.lambda_resource().create_lambda_layer,
            DYNAMO_TABLE_TYPE:
                self.resources_provider.dynamodb().create_tables_by_10,
            CLOUD_WATCH_RULE_TYPE:
                self.resources_provider.cw().create_cloud_watch_rule,
            S3_BUCKET_TYPE:
                self.resources_provider.s3().create_s3_bucket,
            API_GATEWAY_TYPE:
                self.resources_provider.api_gw().create_api_gateway,
            COGNITO_TYPE:
                self.resources_provider.cognito().create_cognito_identity_pool,
            SNS_TOPIC_TYPE:
                self.resources_provider.sns().create_sns_topic,
            SNS_PLATFORM_APPLICATION_TYPE:
                self.resources_provider.sns().create_sns_application,
            SQS_QUEUE_TYPE:
                self.resources_provider.sqs().create_sqs_queue,
            CLOUD_WATCH_ALARM_TYPE:
                self.resources_provider.cw_alarm().create_alarm,
            EBS_TYPE:
                self.resources_provider.ebs().create_ebs,
            STEP_FUNCTION_TYPE:
                self.resources_provider.step_functions().create_state_machine,
            STATE_ACTIVITY_TYPE:
                self.resources_provider.step_functions().create_activities,
            KINESIS_STREAM_TYPE:
                self.resources_provider.kinesis().create_kinesis_stream,
            EC2_INSTANCE_TYPE:
                self.resources_provider.ec2().create_ec2
        }

    def describe_handlers(self):
        return {
            IAM_POLICY:
                self.resources_provider.iam().describe_policy,
            IAM_ROLE:
                self.resources_provider.iam().describe_role,
            LAMBDA_TYPE:
                self.resources_provider.lambda_resource().describe_lambda,
            DYNAMO_TABLE_TYPE:
                self.resources_provider.dynamodb().describe_table,
            CLOUD_WATCH_RULE_TYPE:
                self.resources_provider.cw().describe_rule_from_meta,
            S3_BUCKET_TYPE:
                self.resources_provider.s3().describe_bucket,
            API_GATEWAY_TYPE:
                self.resources_provider.api_gw().describe_api_resources,
            COGNITO_TYPE:
                self.resources_provider.cognito().describe_cognito_pool,
            SNS_TOPIC_TYPE:
                self.resources_provider.sns().describe_sns_from_meta,
            SNS_PLATFORM_APPLICATION_TYPE:
                self.resources_provider.sns().describe_sns_application_from_meta,
            SQS_QUEUE_TYPE:
                self.resources_provider.sqs().describe_queue_from_meta,
            CLOUD_WATCH_ALARM_TYPE:
                self.resources_provider.cw_alarm().describe_alarm,
            EBS_TYPE:
                self.resources_provider.ebs().describe_ebs,
            STEP_FUNCTION_TYPE:
                self.resources_provider.step_functions().describe_step_function,
            STATE_ACTIVITY_TYPE:
                self.resources_provider.step_functions().describe_activity,
            KINESIS_STREAM_TYPE:
                self.resources_provider.kinesis().describe_kinesis_stream,
        }

    def remove_handlers(self):
        return {
            CLOUD_WATCH_ALARM_TYPE:
                self.resources_provider.cw_alarm().remove_alarms,
            API_GATEWAY_TYPE:
                self.resources_provider.api_gw().remove_api_gateways,
            CLOUD_WATCH_RULE_TYPE:
                self.resources_provider.cw().remove_cloud_watch_rules,
            COGNITO_TYPE:
                self.resources_provider.cognito().remove_cognito_identity_pools,
            DYNAMO_TABLE_TYPE:
                self.resources_provider.dynamodb().remove_dynamodb_tables,
            EBS_TYPE:
                self.resources_provider.ebs().remove_ebs_apps,
            EC2_INSTANCE_TYPE:
                self.resources_provider.ec2().remove_ec2_instances,
            IAM_ROLE:
                self.resources_provider.iam().remove_roles,
            IAM_POLICY:
                self.resources_provider.iam().remove_policies,
            KINESIS_STREAM_TYPE:
                self.resources_provider.kinesis().remove_kinesis_streams,
            LAMBDA_LAYER_TYPE:
                self.resources_provider.lambda_resource().remove_lambda_layers,
            LAMBDA_TYPE:
                self.resources_provider.lambda_resource().remove_lambdas,
            S3_BUCKET_TYPE:
                self.resources_provider.s3().remove_buckets,
            SNS_TOPIC_TYPE:
                self.resources_provider.sns().remove_sns_topics,
            SNS_PLATFORM_APPLICATION_TYPE:
                self.resources_provider.sns().remove_sns_application,
            SQS_QUEUE_TYPE:
                self.resources_provider.sqs().remove_queues,
            STEP_FUNCTION_TYPE:
                self.resources_provider.step_functions().remove_state_machines,
            STATE_ACTIVITY_TYPE:
                self.resources_provider.step_functions().remove_activities
        }

    def update_handlers(self):
        return {
            LAMBDA_TYPE:
                self.resources_provider.lambda_resource().update_lambda,
            LAMBDA_LAYER_TYPE:
                self.resources_provider.lambda_resource().update_lambda_layer
        }

    def resource_configuration_processor(self):
        return {
            API_GATEWAY_TYPE:
                self.resources_provider.api_gw().api_gateway_update_processor
        }

    def resource_identifier(self):
        return {
            API_GATEWAY_TYPE:
                self.resources_provider.api_gw().api_resource_identifier,
            COGNITO_TYPE:
                self.resources_provider.cognito().cognito_resource_identifier
        }

    def mapping_applier(self):
        return {
            IAM_ROLE: self.resources_provider.iam().apply_trusted_to_role,
            IAM_POLICY: self.resources_provider.iam().apply_policy_content
        }
