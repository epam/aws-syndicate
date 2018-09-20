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
from boto3 import client

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.ssm_connection')


@apply_methods_decorator(retry)
class SSMConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('ssm', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new SSM connection.')

    def describe_params(self, name=None):
        params = []
        arguments = {}
        if name:
            arguments['Filters'] = [{
                'Key': 'Name',
                'Values': [name]
            }]
        response = self.client.describe_parameters(**arguments)
        params.extend(response.get('Parameters'))
        token = response.get('NextToken')
        while token:
            arguments['NextToken'] = token
            response = self.client.describe_parameters(**arguments)
            token = response.get('NextToken')
            params.extend(response.get('Parameters'))
        return params

    def get_param(self, name, decrypt=False):
        response = self.client.get_parameter(Name=name,
                                             WithDecryption=decrypt)
        if response and response.get('Parameter'):
            return response.get('Parameter').get('Value')

    def put_param(self, name, value, key=None,
                  description='', overwrite=True):
        arguments = {
            'Name': name,
            'Value': value,
            'Type': 'String',
            'Overwrite': overwrite
        }
        if key:
            arguments['KeyId'] = key
            arguments['Type'] = 'SecureString'
        if description:
            arguments['Description'] = description

        self.client.put_parameter(**arguments)

    def delete_param(self, name):
        self.client.delete_parameter(Name=name)

    def delete_parameters(self, names):
        if len(names) > 10:
            raise AssertionError('Too many parameters to delete '
                                 '(max value - 10 items)')
        self.client.delete_parameters(Names=names)
