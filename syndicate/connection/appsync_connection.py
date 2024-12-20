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
import time

from boto3 import client

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.helper import dict_keys_to_camel_case

_LOG = get_logger(__name__)

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
        self.region = region
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
            params['logConfig'] = dict_keys_to_camel_case(log_config)
        if xray_enabled:
            params['xrayEnabled'] = xray_enabled
        if extra_auth_types:
            params['additionalAuthenticationProviders'] = extra_auth_types

        return self.client.create_graphql_api(**params)['graphqlApi']['apiId']

    def create_schema(self, api_id: str, definition: str):
        response = self.client.start_schema_creation(
            apiId=api_id,
            definition=str.encode(definition)
        )
        status = response['status']
        details = response.get('details', '')
        while status == 'PROCESSING':
            time.sleep(2)
            response = self.client.get_schema_creation_status(
                apiId=api_id
            )
            status = response['status']
            details = response.get('details', '')
        return status, details

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

    def create_function(self, api_id: str, func_params: dict):
        params = dict_keys_to_camel_case(func_params)
        params['apiId'] = api_id

        return self.client.create_function(**params)['functionConfiguration']

    def create_resolver(self, api_id: str, type_name: str, field_name: str,
                        kind: str, runtime: str = None,
                        data_source_name: str = None, code: str = None,
                        request_mapping_template: str = None,
                        response_mapping_template: str = None,
                        max_batch_size: int = None,
                        pipeline_config: dict = None):
        params = dict(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name,
            kind=kind
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
        if pipeline_config:
            params['pipelineConfig'] = pipeline_config
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
        def process_apis(resume_token=None):
            pagination_conf = {
                'MaxItems': 60,
                'PageSize': 10
            }
            if resume_token:
                pagination_conf['StartingToken'] = resume_token
            response = paginator.paginate(
                PaginationConfig=pagination_conf
            )
            for page in response:
                apis.extend(
                    [api for api in page['graphqlApis'] if
                     api['name'] == name]
                )
            return response.resume_token

        apis = []
        paginator = self.client.get_paginator('list_graphql_apis')

        next_token = process_apis()
        while next_token:
            next_token = process_apis(next_token)

        if len(apis) == 1:
            return apis[0]
        if len(apis) > 1:
            _LOG.warn(f'AppSync API can\'t be identified unambiguously '
                      f'because there is more than one resource with the name '
                      f'"{name}" in the region {self.region}.')
        else:
            _LOG.warn(f'AppSync API with the name "{name}" '
                      f'not found in the region {self.region}')

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

    def list_functions(self, api_id: str) -> list:
        result = []
        try:
            paginator = self.client.get_paginator('list_functions')
            for response in paginator.paginate(apiId=api_id):
                result.extend(response['functions'])
        except self.client.exceptions.NotFoundException:
            pass

        return result

    def get_schema(self, api_id: str, format: str = None):
        return self.client.get_introspection_schema(
            apiId=api_id,
            format='SDL' if not format else format
        )['schema']

    def list_api_keys(self, api_id: str) -> list:
        return self.client.list_api_keys(apiId=api_id)['apiKeys']

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

    def update_function(self, api_id: str, function_id: str,
                        func_params: dict):
        params = dict_keys_to_camel_case(func_params)
        params.update({
            'apiId': api_id,
            'functionId': function_id
        })
        return self.client.update_function(**params)['functionConfiguration']

    def update_resolver(self, api_id: str, type_name: str, field_name: str,
                        kind: str, runtime: str = None,
                        data_source_name: str = None,
                        request_mapping_template: str = None,
                        response_mapping_template: str = None,
                        code: str = None, max_batch_size: int = None,
                        pipeline_config: dict = None):
        params = dict(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name,
            kind=kind
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
        if max_batch_size:
            params['maxBatchSize'] = max_batch_size
        if pipeline_config:
            params['pipelineConfig'] = pipeline_config

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
            params['logConfig'] = dict_keys_to_camel_case(log_config)
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

    def delete_function(self, api_id: str, func_id: str):
        try:
            return self.client.delete_function(
                apiId=api_id,
                functionId=func_id
            )
        except Exception as e:
            message = ('Cannot delete a function which is currently used by a '
                       'resolver')
            if message in str(e):
                _LOG.warn(str(e))
            else:
                raise

    def delete_resolver(self, api_id: str, type_name: str, field_name: str):

        return self.client.delete_resolver(
            apiId=api_id,
            typeName=type_name,
            fieldName=field_name
        )
