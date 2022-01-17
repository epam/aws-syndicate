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
import re


def is_arn(line):
    return isinstance(line, str) and line.startswith('arn:')


def to_logic_name(resource_type, *parts):
    formatted = []
    for name_part in parts:
        name_components = re.split('[^a-zA-Z0-9]', name_part)
        for component in name_components:
            component_len = len(component)
            if component_len > 1:
                formatted.append(component[0].upper() + component[1:])
            elif component_len == 1:
                formatted.append(component[0].upper())
    return resource_type + ''.join(formatted)


def iam_managed_policy_logic_name(policy_name):
    return to_logic_name('IAMManagedPolicy', policy_name)


def iam_role_logic_name(role_name):
    return to_logic_name('IAMRole', role_name)


def iam_instance_profile_logic_name(role_name):
    return to_logic_name('IAMInstanceProfile', role_name)


def lambda_layer_logic_name(layer_name):
    return to_logic_name('LambdaLayerVersion', layer_name)


def lambda_function_logic_name(function_name):
    return to_logic_name('LambdaFunction', function_name)


def lambda_alias_logic_name(function_name, alias):
    return to_logic_name('LambdaAlias', function_name, alias)


def lambda_publish_version_logic_name(function_name):
    return to_logic_name('LambdaVersion', function_name)


def dynamodb_table_logic_name(table_name):
    return to_logic_name('DynamoDBTable', table_name)


def api_gateway_method_logic_name(path, method):
    return to_logic_name('ApiGatewayMethod', path, method)


def sns_topic_logic_name(topic_name):
    return to_logic_name('SNSTopic', topic_name)


def sqs_queue_logic_name(queue_name):
    return to_logic_name('SQSQueue', queue_name)


def s3_bucket_logic_name(bucket_name):
    return to_logic_name('S3Bucket', bucket_name)


def cloudwatch_rule_logic_name(rule_name):
    return to_logic_name('EventsRule', rule_name)


def kinesis_stream_logic_name(stream_name):
    return to_logic_name('KinesisStream', stream_name)


def batch_compute_env_logic_name(compute_env_name):
    return to_logic_name('BatchComputeEnvironment', compute_env_name)
