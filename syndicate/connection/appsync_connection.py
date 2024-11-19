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
from syndicate.core.helper import dict_keys_to_camel_case

_LOG = get_logger('syndicate.connection.appsync_connection')

DATA_SOURCE_TYPE_CONFIG_MAPPING = {
    'AWS_LAMBDA': 'lambdaConfig',
    'AMAZON_DYNAMODB': 'dynamodbConfig',
    'AMAZON_ELASTICSEARCH': 'elasticsearchConfig',
    'HTTP': 'httpConfig',
    'RELATIONAL_DATABASE': 'relationalDatabaseConfig',
    'AMAZON_OPENSEARCH_SERVICE': 'openSearchServiceConfig',
    'AMAZON_EVENTBRIDGE': 'eventBridgeConfig'
}

REDUNDANT_RESOLVER_EXCEPTION_TEXT = 'Only one resolver is allowed per field'
DATA_SOURCE_EXISTS_EXCEPTION_TEXT = \
    'Data source with name {name} already exists'


@apply_methods_decorator(retry())
class AppSyncConnection(object):
    """ AWS AppSync connection class. """

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('appsync', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new AppSync connection.')

# ------------------------ Create ------------------------

    def create_api(self, name, event_config, tags, owner):
        params = dict(
            name=name
        )
        if event_config:
            params['eventConfig'] = tags
        if tags:
            params['tags'] = tags
        if owner:
            params['ownerContact'] = owner

        return self.client.create_api(**params)

    def create_graphql_api(self, name: str, auth_type: str, tags: dict = None,
                           user_pool_config: dict = None,
                           open_id_config: dict = None,
                           lambda_auth_config: dict = None,
                           log_config: dict = None,
                           xray_enabled: bool = None,
                           extra_auth_types: list = None):
        params = dict(
            name=name,
            authenticationType=auth_type
        )
        if tags:
            params['tags'] = tags
        if user_pool_config:
            user_pool_config = dict_keys_to_camel_case(user_pool_config)
            params['userPoolConfig'] = user_pool_config
        if open_id_config:
            open_id_config = dict_keys_to_camel_case(open_id_config)
            params['openIDConnectConfig'] = open_id_config
        if lambda_auth_config:
            lambda_auth_config = dict_keys_to_camel_case(lambda_auth_config)
            params['lambdaAuthorizerConfig'] = lambda_auth_config
        if log_config:
            params['logConfig'] = log_config
        if xray_enabled:
            params['xrayEnabled'] = xray_enabled
        if extra_auth_types:
            params['additionalAuthenticationProviders'] = extra_auth_types

        return self.client.create_graphql_api(**params)['graphqlApi']['apiId']

    def create_schema(self, api_id: str, definition: str):
        return self.client.start_schema_creation(
            apiId=api_id,
            definition=str.encode(definition)
        )['status']

    def create_type(self, api_id: str, definition: str, format: str):
        params = dict(
            api_id=api_id,
            definition=definition,
            format=format
        )
        return self.client.create_type(**params)['type']

    def create_data_source(self, api_id: str, name: str, source_type: str,
                           source_config: dict = None, description: str = None,
                           service_role_arn: str = None):
        params = dict(
            apiId=api_id,
            name=name,
            type=source_type
        )
        config_key = DATA_SOURCE_TYPE_CONFIG_MAPPING.get(source_type)
        if config_key:
            source_config = dict_keys_to_camel_case(source_config)
            params[config_key] = source_config
        if description:
            params['description'] = description
        if service_role_arn:
            params['serviceRoleArn'] = service_role_arn

        try:
            return self.client.create_data_source(**params)['dataSource']
        except self.client.exceptions.BadRequestException as e:
            error_text = DATA_SOURCE_EXISTS_EXCEPTION_TEXT.format(name=name)
            if error_text in str(e):
                _LOG.warning(error_text)
                return
            else:
                raise e

    def create_resolver(self, api_id: str, type_name: str, field_name: str,
                        runtime: str = None, data_source_name: str = None,
                        code: str = None, request_mapping_template: str = None,
                        response_mapping_template: str = None,
                        kind: str = None, max_batch_size: int = None):
        params = dict(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name
        )
        if runtime:
            params['runtime'] = runtime
        if data_source_name:
            params['dataSourceName'] = data_source_name
        if code:
            params['code'] = code
        if request_mapping_template:
            params['requestMappingTemplate'] = request_mapping_template
        if response_mapping_template:
            params['responseMappingTemplate'] = response_mapping_template
        if kind:
            params['kind'] = kind
        if max_batch_size:
            params['maxBatchSize'] = max_batch_size

        try:
            return self.client.create_resolver(**params)['resolver']
        except self.client.exceptions.BadRequestException as e:
            if REDUNDANT_RESOLVER_EXCEPTION_TEXT in str(e):
                _LOG.warning(f'Only one resolver is allowed per field '
                             f'{field_name}; type {type_name}. '
                             f'Ignoring redundant resolver.')
                return
            else:
                raise e

    def create_api_key(self, api_id: str, description: str = None,
                       expires: int = None):
        params = dict(
            apiId=api_id
        )
        if description:
            params['description'] = description
        if expires:
            params['expires'] = expires

        return self.client.create_api_key(**params)['apiKey']

# ------------------------ Get ------------------------

    def get_graphql_api(self, api_id: str):
        return self.client.get_graphql_api(apiId=api_id)['graphqlApi']

    def get_data_source(self, api_id: str, name: str):
        try:
            return self.client.get_data_source(
                apiId=api_id, name=name)['dataSource']
        except self.client.exceptions.NotFoundException:
            _LOG.warning(f'Data source {name} not found')
            return

    def get_graphql_api_by_name(self, name):
        # TODO change list_graphql_apis to list_apis when upgrade boto3 version
        # TODO implement pagination
        return next((api for api in self.client.list_graphql_apis()[
            'graphqlApis'] if api['name'] == name), None)

    def get_resolver(self, api_id: str, type_name: str, field_name: str):
        try:
            return self.client.get_resolver(
                apiId=api_id,
                typeName=type_name,
                fieldName=field_name
            )['resolver']
        except self.client.exceptions.NotFoundException:
            _LOG.warning(f'Resolver for type {type_name} and field '
                         f'{field_name} not found')
            return

    def list_resolvers(self, api_id: str, type_name: str):
        result = []
        try:
            paginator = self.client.get_paginator('list_resolvers')
            for response in paginator.paginate(apiId=api_id,
                                               typeName=type_name):
                result.extend(response['resolvers'])
        except self.client.exceptions.NotFoundException:
            return

        return result

    def list_data_sources(self, api_id: str) -> list | None:
        result = []
        try:
            paginator = self.client.get_paginator('list_data_sources')
            for response in paginator.paginate(apiId=api_id):
                result.extend(response['dataSources'])
        except self.client.exceptions.NotFoundException:
            return

        return result

    def list_types(self, api_id: str) -> list | None:
        result = []
        try:
            paginator = self.client.get_paginator('list_types')
            for response in paginator.paginate(apiId=api_id, format='JSON'):
                result.extend(response['types'])
        except self.client.exceptions.NotFoundException:
            return

        return result

    def get_schema(self, api_id: str, format: str = None):
        return self.client.get_introspection_schema(
            apiId=api_id,
            format='SDL' if not format else format
        )['schema']
# ------------------------ Update ------------------------

    def update_data_source(self, api_id: str, name: str, source_type: str,
                           source_config: dict = None,
                           description: dict = None,
                           service_role_arn: str = None):
        params = dict(
            apiId=api_id,
            name=name,
            type=source_type
        )
        config_key = DATA_SOURCE_TYPE_CONFIG_MAPPING.get(source_type)
        if config_key:
            source_config = dict_keys_to_camel_case(source_config)
            params[config_key] = source_config
        if description:
            params['description'] = description
        if service_role_arn:
            params['serviceRoleArn'] = service_role_arn

        return self.client.update_data_source(**params)['dataSource']

    def update_resolver(self, api_id: str, type_name: str, field_name: str,
                        runtime: str = None, data_source_name: str = None,
                        request_mapping_template: str = None,
                        response_mapping_template: str = None,
                        code: str = None, kind: str = None,
                        max_batch_size: int = None):
        params = dict(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name
        )
        if runtime:
            params['runtime'] = runtime
        if data_source_name:
            params['dataSourceName'] = data_source_name
        if code:
            params['code'] = code
        if request_mapping_template:
            params['requestMappingTemplate'] = request_mapping_template
        if response_mapping_template:
            params['responseMappingTemplate'] = response_mapping_template
        if kind:
            params['kind'] = kind
        if max_batch_size:
            params['maxBatchSize'] = max_batch_size

        return self.client.update_resolver(**params)['resolver']

    def update_graphql_api(self, api_id: str, name: str,
                           log_config: dict = None,
                           auth_type: str = None,
                           user_pool_config: dict = None,
                           open_id_config: dict = None,
                           lambda_auth_config: dict = None,
                           xray_enabled: bool = None,
                           extra_auth_types: list = None):
        params = dict(
            apiId=api_id,
            name=name
        )
        if auth_type:
            params['authenticationType'] = auth_type
        if user_pool_config:
            user_pool_config = dict_keys_to_camel_case(user_pool_config)
            params['userPoolConfig'] = user_pool_config
        if open_id_config:
            open_id_config = dict_keys_to_camel_case(open_id_config)
            params['openIDConnectConfig'] = open_id_config
        if lambda_auth_config:
            lambda_auth_config = dict_keys_to_camel_case(lambda_auth_config)
            params['lambdaAuthorizerConfig'] = lambda_auth_config
        if log_config:
            params['logConfig'] = log_config
        if xray_enabled:
            params['xrayEnabled'] = xray_enabled
        if extra_auth_types:
            params['additionalAuthenticationProviders'] = extra_auth_types

        return self.client.update_graphql_api(**params)['graphqlApi']['apiId']

# ------------------------ Delete ------------------------

    def delete_graphql_api(self, api_id: str):
        self.client.delete_graphql_api(apiId=api_id)

    def delete_data_source(self, api_id: str, name: str):
        return self.client.delete_data_source(
            apiId=api_id,
            name=name
        )

    def delete_resolver(self, api_id: str, type_name: str, field_name: str):
        return self.client.delete_resolver(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name
        )
