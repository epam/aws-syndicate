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
    print('Incoming event: {}. Pushing to SQS'.format(event))

    queue_name = os.environ['sqs_queue_name']

    sqs_client = boto3.client('sqs')
    name_response = sqs_client.get_queue_url(
        QueueName=queue_name)

    message_body = json.dumps(event)
    messages = []
    for x in range(10):
        messages.append({
            'Id': str(x),
            'MessageBody': message_body
        })

    send_resp = sqs_client.send_message_batch(
        QueueUrl=name_response['QueueUrl'],
        Entries=messages)
    return {
        'body': send_resp
    }
