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
import datetime
import hashlib
import hmac
import json

import requests

from syndicate.connection.api_gateway_connection import ApiGatewayConnection
from syndicate.connection.helper import apply_methods_decorator, retry

SERVICE_NAME = 'apigateway'
HOST_TEMPLATE = 'apigateway.{0}.amazonaws.com'
PROTOCOL = 'https://'
ENCODING = 'utf-8'
ALGORITHM = 'AWS4-HMAC-SHA256'
TERM_STRING = 'aws4_request'
HOST_HEADER_NAME = 'host'
DATE_HEADER_NAME = 'x-amz-date'
AUTH_HEADER_NAME = 'Authorization'
SESSION_HEADER_NAME = 'X-Amz-Security-Token'
SIGNED_HEADERS = ';'.join((HOST_HEADER_NAME, DATE_HEADER_NAME))

ADD_OPERATION = 'add'
REPLACE_OPERATION = 'replace'
REMOVE_OPERATION = 'remove'
RESPONSE_HEADER_PATH = '/responseParameters/gatewayresponse.header.'


def get_host(region):
    return HOST_TEMPLATE.format(region)


def execute_http_request(method, url, headers, data=None):
    response = requests.request(
        method.lower(), url=url, headers=headers, data=data)
    if response.ok:
        return json.loads(response.text)
    else:
        raise AssertionError('request {0} {1} failed. error: \n{2}'
                             .format(method, url, response.text))


def sign(key, msg):
    return hmac.new(key, msg.encode(ENCODING), hashlib.sha256).digest()


def get_signature_key(key, date_stamp, region_name, service_name):
    date = sign(('AWS4' + key).encode(ENCODING), date_stamp)
    region = sign(date, region_name)
    service = sign(region, service_name)
    return sign(service, TERM_STRING)


def get_time_params(time):
    amz_date = time.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = time.strftime('%Y%m%d')
    return amz_date, date_stamp


def create_signature(signing_key, string_to_sign):
    return hmac.new(signing_key, string_to_sign.encode(ENCODING),
                    hashlib.sha256).hexdigest()


def create_canonical_request(method, uri, querystring, headers, payload_hash):
    args = [method, uri, querystring, headers, SIGNED_HEADERS, payload_hash]
    return '\n'.join(args)


def create_canonical_headers(host, amz_date):
    host_header_string = HOST_HEADER_NAME + ':' + host
    date_header_string = DATE_HEADER_NAME + ':' + amz_date
    return host_header_string + '\n' + date_header_string + '\n'


def create_string_to_sign(amz_date, credential_scope, request_hash):
    return '\n'.join([ALGORITHM, amz_date, credential_scope, request_hash])


def create_hash(payload=''):
    return hashlib.sha256(payload).hexdigest()


def create_credential_scope(date_stamp, region):
    return '/'.join([date_stamp, region, SERVICE_NAME, TERM_STRING])


def create_api_headers(amz_date, auth_header, aws_session_token=None):
    headers = {
        DATE_HEADER_NAME: amz_date,
        AUTH_HEADER_NAME: auth_header
    }
    if aws_session_token:
        headers[SESSION_HEADER_NAME] = aws_session_token
    return headers


def create_auth_header(access_key_id, credential_scope, signature):
    template = '{0} Credential={1}/{2}, SignedHeaders={3}, Signature={4}'
    return template.format(ALGORITHM, access_key_id, credential_scope,
                           SIGNED_HEADERS, signature)


@apply_methods_decorator(retry)
class ExtendedApiGatewayConnection(ApiGatewayConnection):
    """
    API Gateway connection class extension. Purpose of this extension is 
    to support api methods, which are currently not supported by boto library. 
    """

    def __init__(self, **kwargs):
        super(ExtendedApiGatewayConnection, self).__init__(**kwargs)
        self.host = get_host(self.region)
        self.endpoint = PROTOCOL + self.host

    def _make_api_call(self, method, uri, payload=None, querystring=''):
        amz_date, date_stamp = get_time_params(datetime.datetime.utcnow())

        canonical_headers = create_canonical_headers(self.host, amz_date)

        string_payload = None
        if payload:
            string_payload = json.dumps(payload)
            payload_hash = create_hash(string_payload)
        else:
            payload_hash = create_hash()

        canonical_request = create_canonical_request(method, uri, querystring,
                                                     canonical_headers,
                                                     payload_hash)

        credential_scope = create_credential_scope(date_stamp, self.region)

        canonical_request_hash = create_hash(canonical_request)

        string_to_sign = create_string_to_sign(amz_date, credential_scope,
                                               canonical_request_hash)

        signing_key = get_signature_key(self.aws_secret_access_key,
                                        date_stamp, self.region,
                                        SERVICE_NAME)
        signature = create_signature(signing_key, string_to_sign)

        auth_header = create_auth_header(self.aws_access_key_id,
                                         credential_scope, signature)

        headers = create_api_headers(amz_date, auth_header,
                                     self.aws_session_token)
        url = self.endpoint + uri
        return execute_http_request(method, url, headers, string_payload)

    def get_gateway_responses(self, api_id):
        """
        Returns collection of the GatewayResponse instances of a api 
        as a responseType-to-GatewayResponse object map of key-value pairs. 
        http://docs.aws.amazon.com/apigateway/api-reference/resource/gateway-responses/
        :type api_id: str 
        :return: 
        """
        uri = '/restapis/{0}/gatewayresponses'.format(api_id)

        return self._make_api_call('GET', uri)

    def put_gateway_responses(self, api_id, response_type, status_code,
                              response_parameters, response_templates):
        """
        Creates a customization of a GatewayResponse of a specified response 
        type and status code on the given api.
        http://docs.aws.amazon.com/apigateway/api-reference/link-relation/gatewayresponse-put/
        :type api_id: str
        :type response_type: str
        :type status_code: str
        :type response_parameters: dict
        :type response_templates: dict 
        :return: 
        """
        uri = '/restapis/{0}/gatewayresponses/{1}'.format(api_id,
                                                          response_type)

        return self._make_api_call('PUT', uri,
                                   {
                                       'statusCode': status_code,
                                       'responseParameters': response_parameters,
                                       'responseTemplates': response_templates
                                   })

    def update_gateway_responses(self, api_id, response_type, operations):
        """
        Updates a gateway responses of a specified response type on the given 
        api.
        http://docs.aws.amazon.com/apigateway/api-reference/link-relation/gatewayresponse-update/
        :type api_id: str
        :type response_type: str
        :type operations: list
        :return: 
        """
        uri = '/restapis/{0}/gatewayresponses/{1}'.format(api_id,
                                                          response_type)
        return self._make_api_call('PATCH', uri,
                                   {'patchOperations': operations})

    def describe_responses(self, api_id):
        response = self.get_gateway_responses(api_id)
        embedded_response = response.get('_embedded')
        if embedded_response:
            items = embedded_response.get('item')
            for item in items:
                item.pop('_links', None)
            return items

    def add_header_for_response(self, api_id, response_type, name, value):
        path = RESPONSE_HEADER_PATH + name

        operation = {
            'op': ADD_OPERATION,
            'path': path,
            'value': value
        }

        return self.update_gateway_responses(api_id, response_type,
                                             [operation])
