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

_LOG = get_logger('syndicate.connection.secrets_manager_connection')


@apply_methods_decorator(retry)
class SecretsManagerConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('secretsmanager', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Secrets Manager connection.')

    def describe_secret(self, secret_id):
        response = self.client.describe_secret(SecretId=secret_id)
        return response

    def get_secret_value(self, secret_id, secret_type='string', version_id=None,
                         version_label=None):
        arguments = {
            'SecretId': secret_id,
        }
        if version_id and version_label:
            raise AssertionError(
                'Version_id and version_label cannot be passed both')
        elif version_id:
            arguments['VersionId'] = version_id
        else:
            arguments['VersionLabel'] = version_label

        if secret_type != 'string' and secret_type != 'binary':
            raise AssertionError(
                'Wrong type value. only string or binary is allowed')

        response = self.client.get_secret_value(**arguments)
        if response and secret_type == 'string':
            return response.get('SecretString')
        if response and secret_type == 'binary':
            return response.get('SecretBinary')

    def create_secret(self, secret_id, secret_value, secret_type='string',
                      description=None, key=None, token=None):
        arguments = {
            'Name': secret_id,
        }
        if description:
            arguments['Description'] = description
        if key:
            arguments['KmsKeyId'] = key
        if token:
            arguments['ClientRequestToken'] = token
        if secret_type == 'string':
            arguments['SecretString'] = secret_value
        elif secret_type == 'binary':
            arguments['SecretBinary'] = secret_value
        else:
            raise AssertionError(
                'Wrong secret_type value. only string or binary is allowed')
        self.client.create_secret(**arguments)

    def put_secret_value(self, secret_id, secret_value, secret_type='string',
                         labels=None):
        if labels:
            labels = set(labels)
            arguments = {
                'SecretId': secret_id,
                'VersionStages': labels
            }
        else:
            arguments = {
                'SecretId': secret_id,
            }

        if secret_type == 'string':
            arguments['SecretString'] = secret_value
        elif secret_type == 'binary':
            arguments['SecretBinary'] = secret_value
        else:
            raise AssertionError(
                'Wrong secret_type value. only string or binary is allowed')
        self.client.put_secret_value(**arguments)

    def delete_secret(self, secret_id, force=True, recovery_days=None):
        self.client.delete_secret(SecretId=secret_id,
                                  ForceDeleteWithoutRecovery=force,
                                  RecoveryWindowInDays=recovery_days)
