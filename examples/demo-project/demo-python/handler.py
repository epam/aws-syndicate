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
import uuid

import boto3


def lambda_handler(event, context):
    obj = {
        'id': str(uuid.uuid1()),
        'event': str(event)
    }

    dynamodb = boto3.resource('dynamodb', region_name=os.environ['region'])

    table = dynamodb.Table('Notifications')

    response = table.put_item(Item=obj)

    print("PutItem succeeded:")
    print(json.dumps(response, indent=4))
