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
from syndicate.core.constants import IAM_AUTH_TYPE, NONE_AUTH_TYPE


class LambdaValidator:
    def __init__(self, name, meta):
        self._name = name,
        self._meta = meta

    def validate(self):
        url_config = self._meta.get('url_config')
        if url_config:
            self._validate_url_config(url_config)
        ephemeral_storage = self._meta.get('ephemeral_storage')
        if ephemeral_storage:
            self._validate_ephemeral_storage(ephemeral_storage)

    def _error(self, message):
        raise AssertionError(message)

    def _validate_url_config(self, url_config):
        if 'auth_type' not in url_config:
            self._error('\'auth_type\' is required in lambda\'s url config')
        auth_types = [IAM_AUTH_TYPE, NONE_AUTH_TYPE]
        if url_config['auth_type'] not in auth_types:
            self._error('\'auth_type\' must be equal to one of these: '
                        f'{", ".join(auth_types)}')
        cors = url_config.get('cors')
        if cors and not isinstance(cors, dict):
            self._error('\'cors\' parameter in lambda config must be a dict')
        if cors:
            allowed_parameters = {'allow_credentials',
                                  'allow_headers', 'allow_methods',
                                  'allow_origins', 'expose_headers',
                                  'max_age'}
            impostors = set(cors.keys()) - allowed_parameters
            if impostors:
                self._error(f'Only these parameters are allowed: '
                            f'{allowed_parameters}')

    def _validate_ephemeral_storage(self, ephemeral_storage):
        if not isinstance(ephemeral_storage, int):
            self._error(f'Ephemeral storage size must an integer but not '
                        f'\'{type(ephemeral_storage).__name__}\'')
        if not (512 <= ephemeral_storage <= 10240):
            self._error('Ephemeral storage size must be between '
                        '512 and 10240 MB')


def validate_lambda(name, meta):
    LambdaValidator(name, meta).validate()
