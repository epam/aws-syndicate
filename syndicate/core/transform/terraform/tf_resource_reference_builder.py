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


def build_function_name_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.function_name}'


def build_function_arn_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.arn}'


def build_lambda_alias_name_ref(alias_name):
    return '${aws_lambda_alias.' + alias_name + '.name}'


def build_lambda_version_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.version}'


def build_function_invoke_arn_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.invoke_arn}'


def build_authorizer_id_ref(authorizer_name):
    return '${aws_api_gateway_authorizer.' + authorizer_name + '.id}'


def build_api_gateway_method_name_reference(method_name):
    return '${aws_api_gateway_method.' + method_name + '.http_method}'


def build_api_gateway_resource_id_ref(resource_name):
    return '${aws_api_gateway_resource.' + resource_name + '.id}'


def build_api_gateway_resource_path_ref(resource_name):
    return '${aws_api_gateway_resource.' + resource_name + '.path}'


def build_rest_api_id_ref(api_name):
    return '${aws_api_gateway_rest_api.' + api_name + '.id}'


def build_sns_topic_arn_ref(sns_topic):
    return '${aws_sns_topic.' + sns_topic + '.arn}'


def build_api_gateway_root_resource_id_ref(api_name):
    return '${aws_api_gateway_rest_api.' + api_name + '.root_resource_id}'


def build_api_gateway_deployment_id_ref(deployment_name):
    return '${aws_api_gateway_deployment.' + deployment_name + '.id}'


def build_cognito_identity_pool_id(pool_name):
    return '${aws_cognito_identity_pool.' + pool_name + '.id}'


def build_ref_to_lambda_layer_arn(layer_name):
    return '${aws_lambda_layer_version.' + layer_name + '.arn}'


def build_role_arn_ref(role_name):
    return '${aws_iam_role.' + role_name + '.arn}'


def build_cloud_watch_event_rule_name_ref(target_rule):
    return '${aws_cloudwatch_event_rule.' + target_rule + '.name}'


def build_resource_arn_ref(tf_resource_type, name):
    return '${' + tf_resource_type + '.' + name + '.arn}'


def build_policy_arn_ref(policy_name):
    return '${aws_iam_policy.' + policy_name + '.arn}'


def build_com_env_arn(com_env_name):
    return '${aws_batch_compute_environment.' + com_env_name + '.arn}'


def build_role_name_ref(role_name):
    return '${aws_iam_role.' + role_name + '.name}'


def build_role_id_ref(role_name):
    return '${aws_iam_role.' + role_name + '.id}'


def build_instance_profile_arn_ref(instance_profile_name):
    return '${aws_iam_instance_profile.' + instance_profile_name + '.arn}'


def build_kinesis_stream_arn_ref(stream_name):
    return '${aws_kinesis_stream.' + stream_name + '.arn}'


def build_bucket_id_ref(bucket_name):
    return '${aws_s3_bucket.' + bucket_name + '.id}'


def build_bucket_arn_ref(bucket_name):
    return '${aws_s3_bucket.' + bucket_name + '.arn}'


def build_dynamo_db_stream_arn_ref(table_name):
    return '${aws_dynamodb_table.' + table_name + '.stream_arn}'


def build_sqs_queue_arn_ref(queue_name):
    return '${aws_sqs_queue.' + queue_name + '.arn}'


def build_sqs_queue_arn_ref(queue_name):
    return '${aws_sqs_queue.' + queue_name + '.arn}'


def build_sqs_queue_id_ref(queue_name):
    return '${aws_sqs_queue.' + queue_name + '.id}'


def build_aws_appautoscaling_target_resource_id_ref(target_name):
    return '${aws_appautoscaling_target.' + target_name + '.resource_id}'


def build_aws_appautoscaling_target_scalable_dimension_ref(target_name):
    return '${aws_appautoscaling_target.' + target_name + '.scalable_dimension}'


def build_aws_appautoscaling_target_service_namespace_ref(target_name):
    return '${aws_appautoscaling_target.' + target_name + '.service_namespace}'
