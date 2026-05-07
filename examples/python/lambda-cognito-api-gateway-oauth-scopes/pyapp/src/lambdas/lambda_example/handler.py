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

cognito_client = boto3.client(
    service_name='cognito-idp',
    region_name=os.environ.get('region', 'eu-central-1')
)
CUP_ID = os.environ.get('cup_id')
CLIENT_ID = os.environ.get('cup_client_id')

PETS = [
    {"id": "1", "name": "Buddy", "species": "dog"},
    {"id": "2", "name": "Whiskers", "species": "cat"},
    {"id": "3", "name": "Goldie", "species": "fish"},
]


def lambda_handler(event, context):
    """
    Handles API Gateway proxy requests.
    By the time this is invoked, Cognito has already validated
    the access_token AND verified the required OAuth scopes.
    """
    http_method = event.get('httpMethod', '')
    path = event.get('resource', '')
    path_params = event.get('pathParameters') or {}
    body = json.loads(event.get('body') or '{}')
    email = body.get('email')
    password = body.get('password')

    # Log token claims for debugging
    claims = (event.get('requestContext', {})
              .get('authorizer', {})
              .get('claims', {}))
    print(f"Token claims: {json.dumps(claims, default=str)}")
    print(f"Scopes in token: {claims.get('scope', 'N/A')}")

    try:
        if path == '/login' and http_method == 'POST':
            return login(email, password)
        elif path == '/signup' and http_method == 'POST':
            return signup(email, password)
        elif path == '/pets' and http_method == 'GET':
            return _response(200, PETS)

        elif path == '/pets' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            new_pet = {
                "id": str(len(PETS) + 1),
                "name": body.get("name", "Unknown"),
                "species": body.get("species", "unknown"),
            }
            PETS.append(new_pet)
            return _response(201, new_pet)

        elif path == '/pets/{pet_id}' and http_method == 'GET':
            pet_id = path_params.get('pet_id')
            pet = next((p for p in PETS if p['id'] == pet_id), None)
            if pet:
                return _response(200, pet)
            return _response(404, {"message": f"Pet {pet_id} not found"})

        else:
            return _response(404, {"message": 'Unknown request path'})

    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {"message": "Internal server error"})


def signup(email, password):
    custom_attr = [{
        'Name': 'email',
        'Value': email
    }]
    try:
        cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=custom_attr)
        cognito_client.admin_confirm_sign_up(
            UserPoolId=CUP_ID, Username=email)
    except Exception as e:
        print(str(e))
        return _response(400, {'message': f'Cannot create user {email}.'})

    return _response(200, {'message': f'User {email} was created.'})


def login(email, password):
    auth_result = cognito_client.admin_initiate_auth(
        UserPoolId=CUP_ID,
        ClientId=CLIENT_ID,
        AuthFlow='ADMIN_USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': email,
            'PASSWORD': password
        })

    return _response(200, {
        'id_token': auth_result['AuthenticationResult']['IdToken'],
        'access_token': auth_result['AuthenticationResult']['AccessToken']
    })


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
