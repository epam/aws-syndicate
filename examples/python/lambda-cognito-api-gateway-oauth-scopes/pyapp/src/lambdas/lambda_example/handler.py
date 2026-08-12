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
from http import HTTPStatus, HTTPMethod

import boto3

from commons.constants import SAMPLE_OBJECTS
from commons.http_utils import build_response, get_authorizer_claims, parse_body


cognito_client = boto3.client(
    service_name='cognito-idp',
    region_name=os.environ.get('region', 'eu-central-1')
)
USER_POOL_ID = os.environ.get('cup_id')
CLIENT_ID = os.environ.get('cup_client_id')


def _sign_up(event):
    body = parse_body(event)
    username = body.get('username')
    password = body.get('password')
    email = body.get('email')
    if not all([username, password, email]):
        raise ValueError('username, password, and email are required')

    try:
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
            TemporaryPassword=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            MessageAction='SUPPRESS',
            DesiredDeliveryMediums=['EMAIL']
        )
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username,
            Password=password,
            Permanent=True
        )
    except Exception as exc:
        return build_response(HTTPStatus.CONFLICT, {'message': str(exc)})

    user = response['User']
    user_sub = next(
        (attr['Value'] for attr in user.get('Attributes', [])
         if attr['Name'] == 'sub'),
        None
    )
    if not user_sub:
        raise RuntimeError('Sub not found.')

    return build_response(HTTPStatus.CREATED, {
        'userSub': user_sub,
        'username': user['Username'],
        'userConfirmed': user.get('UserStatus') == 'CONFIRMED'
    })


def _sign_in(event):
    body = parse_body(event)
    username = body.get('username')
    password = body.get('password')
    if not all([username, password]):
        raise ValueError('username and password are required')

    try:
        auth_result = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            },
        )
    except Exception as exc:
        return build_response(HTTPStatus.UNAUTHORIZED, {'message': str(exc)})

    tokens = auth_result['AuthenticationResult']
    return build_response(HTTPStatus.OK, {
        'idToken': tokens['IdToken'],
        'accessToken': tokens['AccessToken'],
        'refreshToken': tokens['RefreshToken'],
        'expiresIn': tokens['ExpiresIn'],
        'tokenType': tokens.get('TokenType', 'Bearer')
    })


def _refresh_token(event):
    body = parse_body(event)
    username = body.get('username')
    refresh_token = body.get('refreshToken')
    if not all([username, refresh_token]):
        raise ValueError('username and refreshToken are required')

    try:
        auth_result = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'USERNAME': username,
                'REFRESH_TOKEN': refresh_token,
            },
        )
    except Exception as exc:
        return build_response(HTTPStatus.UNAUTHORIZED, {'message': str(exc)})

    tokens = auth_result['AuthenticationResult']
    return build_response(HTTPStatus.OK, {
        'idToken': tokens['IdToken'],
        'accessToken': tokens['AccessToken'],
        'expiresIn': tokens['ExpiresIn'],
        'tokenType': tokens.get('TokenType', 'Bearer'),
    })


def _sign_out(event):
    claims = get_authorizer_claims(event)
    username = claims.get('username')
    if not username:
        return build_response(
            HTTPStatus.UNAUTHORIZED, {'message': 'Unauthorized'}
        )

    try:
        cognito_client.admin_user_global_sign_out(
            UserPoolId=USER_POOL_ID,
            Username=username,
        )
    except Exception as exc:
        return build_response(HTTPStatus.UNAUTHORIZED, {'message': str(exc)})

    return build_response(HTTPStatus.NO_CONTENT)


def _list_objects(event):
    return build_response(HTTPStatus.OK, SAMPLE_OBJECTS)


def lambda_handler(event, context):
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    route = (http_method, path)

    claims = get_authorizer_claims(event)
    if claims:
        print(f'Token claims: {json.dumps(claims, default=str)}')
        print(f"Scopes in token: {claims.get('scope', 'N/A')}")

    handlers = {
        (HTTPMethod.POST, '/auth/sign-up'): _sign_up,
        (HTTPMethod.POST, '/auth/sign-in'): _sign_in,
        (HTTPMethod.POST, '/auth/refresh-token'): _refresh_token,
        (HTTPMethod.POST, '/auth/sign-out'): _sign_out,
        (HTTPMethod.GET, '/objects/public'): _list_objects,
        (HTTPMethod.GET, '/objects/secured-by-id-token'): _list_objects,
        (HTTPMethod.GET, '/objects/secured-by-access-token'): _list_objects
    }

    handler = handlers.get(route)
    if handler is None:
        return build_response(
            HTTPStatus.NOT_FOUND,
            {'message': f'Route not implemented: {http_method} {path}'}
        )

    try:
        return handler(event)
    except ValueError as exc:
        return build_response(HTTPStatus.BAD_REQUEST, {'message': str(exc)})
    except Exception as exc:
        print(f'Error handling {http_method} {path}: {exc}')
        return build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'message': 'Internal server error'}
        )
