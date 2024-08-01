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
import os

import boto3


def lambda_handler(event, context):
    print(event)
    body = json.loads(event['body'])
    email = body.get('email')
    password = body.get('password')

    auth_result = admin_initiate_auth(username=email, password=password)
    if auth_result:
        id_token = auth_result['AuthenticationResult']['IdToken']
    else:
        id_token = None

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(id_token)
    }


def admin_initiate_auth(username, password):
    auth_params = {
        'USERNAME': username,
        'PASSWORD': password
    }
    cognito_client = boto3.client('cognito-idp',
                                  os.environ.get('region', 'eu-central-1'))
    result = cognito_client.admin_initiate_auth(
        UserPoolId=os.environ.get('cup_id'),
        ClientId=os.environ.get('cup_client_id'),
        AuthFlow='ADMIN_NO_SRP_AUTH', AuthParameters=auth_params)
    return result
