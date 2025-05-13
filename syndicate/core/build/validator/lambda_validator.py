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
from syndicate.exceptions import ResourceMetadataError
from syndicate.core.constants import IAM_AUTH_TYPE, NONE_AUTH_TYPE, \
    LAMBDA_ARCHITECTURE_LIST, DYNAMO_DB_TRIGGER, CLOUD_WATCH_RULE_TRIGGER, \
    DYNAMODB_TRIGGER_REQUIRED_PARAMS, EVENT_BRIDGE_RULE_TRIGGER, \
    CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS, S3_TRIGGER, \
    S3_TRIGGER_REQUIRED_PARAMS, SNS_TOPIC_TRIGGER, SNS_TRIGGER_REQUIRED_PARAMS, \
    KINESIS_TRIGGER, KINESIS_TRIGGER_REQUIRED_PARAMS, SQS_TRIGGER, \
    SQS_TRIGGER_REQUIRED_PARAMS

RESOURCE_TYPE_KEY = 'resource_type'

TRIGGER_REQUIRED_PARAMS_MAPPING = {
        DYNAMO_DB_TRIGGER: DYNAMODB_TRIGGER_REQUIRED_PARAMS,
        CLOUD_WATCH_RULE_TRIGGER: CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS,
        EVENT_BRIDGE_RULE_TRIGGER: CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS,
        S3_TRIGGER: S3_TRIGGER_REQUIRED_PARAMS,
        SNS_TOPIC_TRIGGER: SNS_TRIGGER_REQUIRED_PARAMS,
        KINESIS_TRIGGER: KINESIS_TRIGGER_REQUIRED_PARAMS,
        SQS_TRIGGER: SQS_TRIGGER_REQUIRED_PARAMS
    }


class LambdaValidator:
    def __init__(self, name, meta):
        self._name = name
        self._meta = meta

    def validate(self):
        url_config = self._meta.get('url_config')
        if url_config:
            self._validate_url_config(url_config)

        ephemeral_storage = self._meta.get('ephemeral_storage')
        if ephemeral_storage:
            self._validate_ephemeral_storage(ephemeral_storage)

        architectures = self._meta.get('architectures')
        if architectures:
            self._validate_architecture(architectures)

        event_sources = self._meta.get('event_sources')
        if event_sources:
            self._validate_event_sources(event_sources)

    def _error(self, message):
        raise ResourceMetadataError(message)

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

    def _validate_architecture(self, architectures):
        for architecture in architectures:
            if architecture not in LAMBDA_ARCHITECTURE_LIST:
                self._error(f'Specified unsupported architecture: '
                            f'"{architecture}". Currently supported '
                            f'architectures: {LAMBDA_ARCHITECTURE_LIST}')

    def _validate_event_sources(self, event_sources: list[dict]) -> None:
        errors = []
        for index, event_source in enumerate(event_sources, 1):
            if not isinstance(event_source, dict):
                errors.append(
                    f"Event source configuration with index '{index}' is "
                    f"invalid. Expected type: 'map(object)' actual: "
                    f"'{type(event_source).__name__}'"
                )
                continue

            resource_type = event_source.get(RESOURCE_TYPE_KEY)
            if resource_type is None:
                errors.append(
                    f"Event source configuration with index '{index}' is "
                    f"invalid. The parameter '{RESOURCE_TYPE_KEY}' is "
                    f"mandatory."
                )
                continue
            if resource_type not in TRIGGER_REQUIRED_PARAMS_MAPPING:
                errors.append(
                    f"Event source configuration with index '{index}' is "
                    f"invalid. Trigger type '{resource_type}' is not "
                    f"supported. Supported trigger types: "
                    f"{list(TRIGGER_REQUIRED_PARAMS_MAPPING.keys())}"
                )
                continue

            req_params = TRIGGER_REQUIRED_PARAMS_MAPPING[resource_type]
            req_params.insert(0, RESOURCE_TYPE_KEY)
            existing_params = list(event_source.keys())
            for each in req_params:
                if each not in existing_params:
                    errors.append(
                        f"Event source configuration with index '{index}' is "
                        f"invalid. Not all required parameters specified. "
                        f"Required parameters: "
                        f"{req_params}. "
                        f"Given parameters: {existing_params}."
                    )
                    break

        if errors:
            errors_string = '\n'.join(errors)
            self._error(
                f"Lambda '{self._name}' event sources haven't passed "
                f"validation.\n{errors_string}")


def validate_lambda(name, meta):
    LambdaValidator(name, meta).validate()
