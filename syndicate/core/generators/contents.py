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
import json

from syndicate.core.conf.validator import LAMBDAS_ALIASES_NAME_CFG
from syndicate.core.generators import _alias_variable

POLICY_LAMBDA_BASIC_EXECUTION = "lambda-basic-execution"

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name

PYTHON_LAMBDA_HANDLER_TEMPLATE = """import json


def lambda_handler(event, context):
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
"""

NODEJS_LAMBDA_HANDLER_TEMPLATE = """exports.handler = async (event) => {
    // TODO implement
    const response = {
        statusCode: 200,
        body: JSON.stringify('Hello from Lambda!'),
    };
    return response;
};
"""


def _stringify(dict_content):
    return json.dumps(dict_content, indent=2)


def _generate_python_node_lambda_config(lambda_name, lambda_relative_path):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'handler.lambda_handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': 'python3.7',
        'memory': 128,
        'timeout': 100,
        'lambda_path': lambda_relative_path,
        'dependencies': [],
        'event_sources': [],
        'env_variables': {},
        'publish_version': True,
        'alias': _alias_variable(LAMBDAS_ALIASES_NAME_CFG)
    })


def _get_lambda_default_policy():
    return _stringify({
        POLICY_LAMBDA_BASIC_EXECUTION: {
            'policy_content': {
                "Statement": [
                    {
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "dynamodb:Get*",
                            "dynamodb:Put*",
                            "dynamodb:Describe*",
                            "xray:PutTraceSegments",
                            "xray:PutTelemetryRecords",
                            "kms:Decrypt"
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ],
                "Version": "2012-10-17"},
            "resource_type": "iam_policy"
        }
    })


def _generate_lambda_role_config(role_name):
    return _stringify({
        role_name: {
            "predefined_policies": [],
            "principal_service": "lambda",
            "custom_policies": [
                POLICY_LAMBDA_BASIC_EXECUTION
            ],
            "resource_type": "iam_role",
            "allowed_accounts": [
                "${account_id}"
            ]
        }
    })
