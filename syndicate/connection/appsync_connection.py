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

    def create_graphql_api(self, name: str, auth_type: str, tags: dict,
                           user_pool_config: dict, open_id_config: dict,
                           lambda_auth_config: dict, log_config: dict,
                           api_type: str = 'GRAPHQL'):
        params = dict(
            name=name,
            authenticationType=auth_type,
            apiType=api_type
        )
        if tags:
            params['tags'] = tags
        if user_pool_config:
            params['userPoolConfig'] = user_pool_config
        if open_id_config:
            params['openIDConnectConfig'] = open_id_config
        if lambda_auth_config:
            params['lambdaAuthorizerConfig'] = lambda_auth_config
        if log_config:
            params['logConfig'] = log_config

        return self.client.create_graphql_api(**params)['graphqlApi']['apiId']

    def create_schema(self, api_id: str, definition: str):
        return self.client.start_schema_creation(
            apiId=api_id,
            definition=definition.encode('utf-8')
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
                           service_role_arn: str = None,
                           metrics_config: str = 'DISABLED'):
        params = dict(
            api_id=api_id,
            name=name,
            type=source_type,
            metrics_config=metrics_config
        )
        config_key = DATA_SOURCE_TYPE_CONFIG_MAPPING.get(source_type)
        if config_key:
            params[config_key] = source_config
        if description:
            params['description'] = description
        if service_role_arn:
            params['serviceRoleArn'] = service_role_arn

        return self.client.create_data_source(**params)['dataSource']

    def create_resolver(self, api_id: str, type_name: str, field_name: str,
                        runtime: str = None, data_source_name: str = None,
                        code: str = None, metrics_config: str = 'DISABLED',
                        request_mapping_template: str = None,
                        response_mapping_template: str = None):
        params = dict(
            api_id=api_id,
            type_name=type_name,
            field_name=field_name,
            metrics_config=metrics_config
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

        return self.client.create_resolver(**params)['resolver']

# ------------------------ Get ------------------------

    def get_graphql_api(self, api_id: str):
        return self.client.get_graphql_api(apiId=api_id)['graphqlApi']

    def get_data_source(self, api_id: str, name: str):
        return self.client.get_data_source(
            apiId=api_id, name=name)['dataSource']

    def delete_graphql_api(self, api_id: str):
        try:
            self.client.delete_graphql_api(apiId=api_id)
        except self.client.exceptions.NotFoundException:
            _LOG.info(f'GraphQL API {api_id} already deleted.')
            return
