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

_LOG = get_logger('syndicate.connection.kms_connection')


@apply_methods_decorator(retry)
class KMSConnection(object):
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('kms', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new KMS connection.')

    def list_keys(self):
        keys = []
        response = self.client.list_keys()
        if 'Keys' in response:
            keys.extend(response.get('Keys'))
        while response.get('Truncated'):
            response = self.client.list_keys(Marker=response.get('NextMarker'))
            if 'Keys' in response:
                keys.extend(response.get('Keys'))
        return keys

    def describe_key(self, key_id):
        response = self.client.describe_key(KeyId=key_id)
        if response:
            return response.get('KeyMetadata')

    def create_key(self, description='', key_usage='ENCRYPT_DECRYPT',
                   origin='AWS_KMS', policy=None):
        arguments = {
            'Description': description,
            'KeyUsage': key_usage,
            'Origin': origin
        }
        if policy:
            arguments['Policy'] = policy

        response = self.client.create_key(**arguments)

        if response and response.get('KeyMetadata'):
            return response.get('KeyMetadata').get('KeyId')

    def schedule_key_deletion(self, key, days=7):
        self.client.schedule_key_deletion(KeyId=key, PendingWindowInDays=days)

    def list_aliases(self):
        aliases = []
        response = self.client.list_aliases()
        if 'Aliases' in response:
            aliases.extend(response.get('Aliases'))
        while response.get('Truncated'):
            response = self.client.list_aliases(
                Marker=response.get('NextMarker'))
            if 'Aliases' in response:
                aliases.extend(response.get('Aliases'))
        return aliases

    def create_alias(self, alias, key):
        self.client.create_alias(AliasName=alias, TargetKeyId=key)

    def update_alias(self, alias, key):
        self.client.update_alias(AliasName=alias, TargetKeyId=key)

    def delete_alias(self, alias):
        self.client.delete_alias(AliasName=alias)
