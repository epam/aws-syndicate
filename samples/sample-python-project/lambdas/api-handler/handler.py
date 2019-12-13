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
