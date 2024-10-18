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
import time
from hashlib import md5

from botocore.exceptions import ClientError

from syndicate.commons import deep_get
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import (
    SOURCE_ARN_DEEP_KEY, SECURITY_SCHEMAS_DEEP_KEY,
    API_GW_DEFAULT_THROTTLING_RATE_LIMIT,
    API_GW_DEFAULT_THROTTLING_BURST_LIMIT
)
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
from syndicate.connection.api_gateway_connection import ApiGatewayV2Connection, \
    ApiGatewayConnection
from syndicate.core.resources.lambda_resource import LambdaResource

API_REQUIRED_PARAMS = ['resources', 'deploy_stage']

_LOG = get_logger('syndicate.core.resources.api_gateway_resource')
USER_LOG = get_user_logger()

SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',
                     'HEAD', 'ANY']
SUPPORTED_STAGE_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',
                           'HEAD']
_CORS_HEADER_NAME = 'Access-Control-Allow-Origin'
_CORS_HEADER_VALUE = "'*'"
_COGNITO_AUTHORIZER_TYPE = 'COGNITO_USER_POOLS'
_CUSTOM_AUTHORIZER_TYPE = 'CUSTOM'

X_SDCT_EXTENSION_KEY = 'x-syndicate-cognito-userpool-names'
PROVIDER_ARNS_KEY = 'providerARNs'

POLICY_STATEMENT_SINGLETON = 'policy_statement_singleton'

_REQUEST_VALIDATORS = {
    'NONE': {
        'validate_request_body': False,
        'validate_request_parameters': False,
        'id': None
    },
    'Validate body': {
        'validate_request_body': True,
        'validate_request_parameters': False,
        'id': None
    },
    'Validate query string parameters and headers': {
        'validate_request_parameters': True,
        'validate_request_body': False,
        'id': None
    },
    'Validate body, query string parameters, and headers': {
        'validate_request_body': True,
        'validate_request_parameters': True,
        'id': None
    }
}

_DISABLE_THROTTLING_VALUE = -1
OPERATION_REPLACE = 'replace'


class ApiGatewayResource(BaseResource):

    def __init__(self, apigw_conn: ApiGatewayConnection,
                 apigw_v2_conn: ApiGatewayV2Connection,
                 lambda_res: LambdaResource,
                 cognito_res, account_id, region) -> None:
        self.connection = apigw_conn
        self.lambda_res = lambda_res
        self.cognito_res = cognito_res
        self.account_id = account_id
        self.region = region
        self.apigw_v2 = apigw_v2_conn

    def _create_default_validators(self, api_id):
        for name, options in _REQUEST_VALIDATORS.items():
            _id = self.connection.create_request_validator(
                api_id, name, options['validate_request_body'],
                options['validate_request_parameters']
            )
            options['id'] = _id

    def _retrieve_request_validator_id(self, api_id, request_validator=None):
        request_validator = request_validator or {}
        if not request_validator:
            return
        validate_request_body = request_validator.get(
            'validate_request_body') or False
        validate_request_parameters = request_validator.get(
            'validate_request_parameters') or False
        name = request_validator.get('name')

        if name:
            return self.connection.create_request_validator(
                api_id, name, validate_request_body,
                validate_request_parameters)
        for validators in _REQUEST_VALIDATORS.values():
            if (validators['validate_request_body'] == validate_request_body) \
                    and (validators[
                             'validate_request_parameters'] == validate_request_parameters):
                return validators['id']

    def api_resource_identifier(self, name, output=None):
        if output:
            # api currently is not located in different regions
            # process only first object
            api_output = list(output.items())[0][1]
            # find id from the output
            return api_output['description']['id']
        # if output is not provided - try to get API by name
        # cause there is no another option
        return self.connection.get_api_id(name)

    def create_api_gateway(self, args):
        """ Create api gateway in pool in sub processes.
    
        :type args: list
        """
        return self.create_pool(self._create_api_gateway_from_meta, args, 1)

    def create_api_gateway_openapi(self, args):
        """ Create OpenAPI api gateway in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_api_gateway_openapi_from_meta,
                                args, 1)

    def api_gateway_update_processor(self, args):
        return self.create_pool(self._create_or_update_api_gateway, args, 1)

    def update_api_gateway_openapi(self, args):
        return self.create_pool(self._update_api_gateway_openapi_from_meta, args, 1)

    @unpack_kwargs
    def _create_or_update_api_gateway(self, name, meta,
                                      current_configurations):
        if current_configurations:
            # api currently is not located in different regions
            # process only first object
            api_output = list(current_configurations.items())[0][1]
            # find id from the output
            api_id = api_output['description']['id']
            # check that api does not exist
            api_response = self.connection.get_api(api_id)
            if api_response:
                # find all existing resources
                existing_resources = api_output['description']['resources']
                existing_paths = [i['path'] for i in existing_resources]
                meta_api_resources = meta['resources']
                resources_statement_singleton = meta.get(
                    POLICY_STATEMENT_SINGLETON)
                api_resp = meta.get('api_method_responses')
                api_integration_resp = meta.get(
                    'api_method_integration_responses')
                api_resources = {}
                for resource_path, resource_meta in meta_api_resources.items():
                    if resource_path not in existing_paths:
                        api_resources[resource_path] = resource_meta
                if api_resources:
                    _LOG.debug(
                        'Going to continue deploy API Gateway {0} ...'.format(
                            api_id))
                    args = self.__prepare_api_resources_args(
                        api_id=api_id,
                        api_resources=api_resources,
                        api_resp=api_resp,
                        api_integration_resp=api_integration_resp,
                        resources_statement_singleton=resources_statement_singleton)
                    self.create_pool(self._create_resource_from_metadata,
                                     args, 1)
                    # add headers
                    # waiter b4 customization
                    time.sleep(10)
                    _LOG.debug(
                        'Customizing API Gateway {0} responses...'.format(
                            api_id))
                else:
                    # all resources created, but need to override
                    api_resources = meta_api_resources
                # _customize_gateway_responses call is commented due to
                # botocore InternalFailure while performing the call.
                # will be fixed later
                # _customize_gateway_responses(api_id)
                # deploy api
                _LOG.debug('Deploying API Gateway {0} ...'.format(api_id))
                self.__deploy_api_gateway(api_id, meta, api_resources)
                return self.describe_api_resources(api_id=api_id, meta=meta,
                                                   name=name)
            else:
                # api does not exist, so create a new
                return self._create_api_gateway_from_meta(
                    {'name': name, 'meta': meta})
        else:
            # object is not present, so just create a new api
            return self._create_api_gateway_from_meta(
                {'name': name, 'meta': meta})

    def _escape_path(self, parameter):
        index = parameter.find('/', 0)
        if index == -1:
            return parameter
        parameter = parameter[:index] + '~1' + parameter[index + 1:]
        return self._escape_path(parameter)

    def configure_resources(self, api_id, stage_name, api_resources):
        for resource_path, resource_meta in api_resources.items():
            for method_name, method_meta in resource_meta.items():
                if method_name in SUPPORTED_METHODS:
                    cache_configuration = method_meta.get(
                        'cache_configuration')
                    throttling_configuration = method_meta.get(
                        'throttling_configuration')
                    cache_ttl_setting = cache_configuration.get(
                        'cache_ttl_sec') if cache_configuration else None
                    encrypt_cache_data = cache_configuration.get(
                        'encrypt_cache_data') if cache_configuration else None
                    throttling_enabled = throttling_configuration.get(
                        'throttling_enabled') if throttling_configuration \
                        else None
                    throttling_rate_limit = throttling_configuration.get(
                        'throttling_rate_limit',
                        API_GW_DEFAULT_THROTTLING_RATE_LIMIT) if (
                        throttling_configuration and throttling_enabled) else \
                        _DISABLE_THROTTLING_VALUE
                    throttling_burst_limit = throttling_configuration.get(
                        'throttling_burst_limit',
                        API_GW_DEFAULT_THROTTLING_BURST_LIMIT) if (
                        throttling_configuration and throttling_enabled) else \
                        _DISABLE_THROTTLING_VALUE

                    patch_operations = []
                    escaped_resource = self._escape_path(resource_path)
                    methods_to_configure = SUPPORTED_STAGE_METHODS \
                        if method_name == 'ANY' else [method_name]
                    for method in methods_to_configure:
                        if cache_ttl_setting is not None:
                            _LOG.info(f'Configuring cache for {resource_path};'
                                      f' TTL: {cache_ttl_setting}')
                            patch_operations.append({
                                'op': OPERATION_REPLACE,
                                'path': f'/{escaped_resource}/{method}'
                                        f'/caching/ttlInSeconds',
                                'value': str(cache_ttl_setting),
                            })
                            patch_operations.append({
                                'op': OPERATION_REPLACE,
                                'path': f'/{escaped_resource}/{method}'
                                        f'/caching/enabled',
                                'value': 'True',
                            })
                        if encrypt_cache_data is not None:
                            patch_operations.append({
                                'op': OPERATION_REPLACE,
                                'path': f'/{escaped_resource}/{method}'
                                        f'/caching/enabled',
                                'value': 'True',
                            })
                            patch_operations.append({
                                'op': OPERATION_REPLACE,
                                'path': f'/{escaped_resource}/{method}'
                                        f'/caching/dataEncrypted',
                                'value': 'true' if bool(
                                    encrypt_cache_data) else 'false'
                            })

                        if throttling_enabled:
                            _LOG.info(
                                f'Configuring throttling for {resource_path}; '
                                f'rateLimit: {throttling_rate_limit}; '
                                f'burstLimit: {throttling_burst_limit}')
                        else:
                            _LOG.info(
                                f'Throttling for {resource_path} disabled.')
                        patch_operations.append({
                            'op': OPERATION_REPLACE,
                            'path': f'/{escaped_resource}/{method}'
                                    f'/throttling/rateLimit',
                            'value': str(throttling_rate_limit),
                        })
                        patch_operations.append({
                            'op': OPERATION_REPLACE,
                            'path': f'/{escaped_resource}/{method}/'
                                    f'throttling/burstLimit',
                            'value': str(throttling_burst_limit),
                        })

                    if patch_operations:
                        self.connection.update_configuration(
                            rest_api_id=api_id,
                            stage_name=stage_name,
                            patch_operations=patch_operations
                        )
                    _LOG.info(f'Resource {resource_path} was configured')

    @unpack_kwargs
    def _create_api_gateway_from_meta(self, name, meta):
        """ Create API Gateway with all specified meta.
    
        :type name: str
        :type meta: dict
        """
        validate_params(name, meta, API_REQUIRED_PARAMS)

        api_resources = meta['resources']
        # whether to put a wildcard in lambda resource-based policy permissions
        resources_permission_singleton = meta.get(POLICY_STATEMENT_SINGLETON)
        api_gw_describe = self.describe_api_resources(name, meta)
        if api_gw_describe:
            _LOG.info(f'Api gateway with name \'{name}\' exists. Returning')
            return api_gw_describe
        _LOG.info(f'Api gateway with name \'{name}\' does not exist. Creating')
        api_item = self.connection.create_rest_api(
            api_name=name,
            binary_media_types=meta.get('binary_media_types'),
            tags=meta.get('tags'))
        api_id = api_item['id']

        # create default request validators
        self._create_default_validators(api_id)

        # set minimumCompressionSize if the param exists
        minimum_compression_size = meta.get('minimum_compression_size', None)
        if not minimum_compression_size:
            _LOG.debug("No minimal_compression_size param - "
                       "compression isn't enabled")
        self.connection.update_compression_size(
            rest_api_id=api_id,
            compression_size=minimum_compression_size)

        # deploy authorizers
        authorizers = meta.get('authorizers', {})
        for key, val in authorizers.items():
            uri = None
            provider_arns = []
            if val.get('type') == _COGNITO_AUTHORIZER_TYPE:
                for pool in val.get('user_pools'):
                    user_pool_id = self.cognito_res.get_user_pool_id(pool)
                    provider_arns.append(
                        f'arn:aws:cognito-idp:{self.region}:{self.account_id}:'
                        f'userpool/{user_pool_id}')
            else:
                lambda_version = val.get('lambda_version')
                lambda_name = val.get('lambda_name')
                lambda_alias = val.get('lambda_alias')
                lambda_arn = self.lambda_res. \
                    resolve_lambda_arn_by_version_and_alias(lambda_name,
                                                            lambda_version,
                                                            lambda_alias)
                uri = f'arn:aws:apigateway:{self.region}:lambda:path/' \
                      f'2015-03-31/functions/{lambda_arn}/invocations'
                api_source_arn = (f'arn:aws:execute-api:{self.region}:'
                                  f'{self.account_id}:{api_id}/*/*')
                self.lambda_res.add_invocation_permission(
                    statement_id=api_id,
                    name=lambda_arn,
                    source_arn=api_source_arn,
                    principal='apigateway.amazonaws.com')

            self.connection.create_authorizer(api_id=api_id, name=key,
                                              type=val['type'],
                                              authorizer_uri=uri,
                                              identity_source=val.get(
                                                  'identity_source'),
                                              ttl=val.get('ttl'),
                                              provider_arns=provider_arns)

        models = meta.get('models')
        if models:
            args = [{'api_id': api_id, 'models': {k: v}} for k, v in
                    models.items()]
            self.create_pool(self._create_model_from_metadata, args, 1)
        if api_resources:
            api_resp = meta.get('api_method_responses')
            api_integration_resp = meta.get('api_method_integration_responses')
            args = self.__prepare_api_resources_args(
                api_id, api_resources, api_resp, api_integration_resp,
                resources_permission_singleton)
            self.create_pool(self._create_resource_from_metadata, args, 1)
        else:
            _LOG.info('There is no resources in %s API Gateway description.',
                      name)
        # add headers
        # waiter b4 customization
        time.sleep(10)
        _LOG.debug('Customizing API Gateway responses...')
        # _customize_gateway_responses call is commented due to botocore
        # InternalFailure while performing the call. will be fixed later
        # _customize_gateway_responses(api_id)
        # deploy api
        self.__deploy_api_gateway(api_id, meta, api_resources)
        return self.describe_api_resources(api_id=api_id, meta=meta, name=name)

    @unpack_kwargs
    def _create_api_gateway_openapi_from_meta(self, name, meta):
        openapi_context = meta.get('definition')
        deploy_stage = meta.get('deploy_stage')

        self._resolve_cup_ids(openapi_context)

        api_gw_describe = self.describe_api_resources(name, meta)
        if api_gw_describe:
            _LOG.info(f'Api gateway with name \'{name}\' exists. Returning')
            return api_gw_describe

        _LOG.info(f'Api gateway with name \'{name}\' does not exist. Creating')
        api_id = self.connection.create_openapi(openapi_context)
        _LOG.debug('Applying tags')
        self.connection.tag_openapi(openapi_id=api_id, tags=meta.get('tags'))
        self.connection.deploy_api(api_id, deploy_stage)

        api_lambdas_arns = self.extract_api_gateway_lambdas_arns(
            openapi_context)
        self.create_lambdas_permissions(api_id, api_lambdas_arns, '/*/*/*')
        api_lambda_auth_arns = self.extract_api_gateway_lambda_auth_arns(
            openapi_context)
        self.create_lambdas_permissions(api_id, api_lambda_auth_arns, '/*/*')

        return self.describe_api_resources(api_id=api_id, meta=meta, name=name)

    @unpack_kwargs
    def _update_api_gateway_openapi_from_meta(self, name, meta, context):
        api_id = self.connection.get_api_id(name)
        openapi_context = meta.get('definition')
        deploy_stage = meta.get('deploy_stage')

        self._resolve_cup_ids(openapi_context)

        self.connection.update_openapi(api_id, openapi_context)
        self.connection.deploy_api(api_id, deploy_stage)

        api_lambdas_arns = self.extract_api_gateway_lambdas_arns(
            openapi_context
        )
        self.create_lambdas_permissions(api_id, api_lambdas_arns, '/*/*/*')
        api_lambda_auth_arns = self.extract_api_gateway_lambda_auth_arns(
            openapi_context
        )
        self.create_lambdas_permissions(api_id, api_lambda_auth_arns, '/*/*')

        return self.describe_api_resources(api_id=api_id, meta=meta, name=name)

    def _resolve_cup_ids(self, openapi_context):
        _LOG.debug('Going to resolve Cognito User Pools ARNs')
        security_schemes = \
            openapi_context.get('components', {}).get('securitySchemes', {})

        authorizers = [
            value['x-amazon-apigateway-authorizer']
            for _, value in security_schemes.items()
            if (value.get('x-amazon-apigateway-authtype') ==
                _COGNITO_AUTHORIZER_TYPE.lower()
                and 'x-amazon-apigateway-authorizer' in value)]

        for authorizer in authorizers:
            pools_names = provider_arns = None
            if authorizer.get('type') == _COGNITO_AUTHORIZER_TYPE.lower():
                pools_names = authorizer.get(X_SDCT_EXTENSION_KEY)
                provider_arns = authorizer.get(PROVIDER_ARNS_KEY)
            new_provider_arns = []
            if pools_names:
                for pool_name in pools_names:
                    _LOG.debug(f'Resolving ARN for Cognito User Pool by name '
                               f'{pool_name}')
                    pool_id = self.cognito_res.get_user_pool_id(pool_name)
                    if pool_id:
                        new_provider_arns.append(
                            f'arn:aws:cognito-idp:{self.region}:'
                            f'{self.account_id}:userpool/{pool_id}')
                    else:
                        USER_LOG.warn(f'Can\'t resolve Cognito User Pool ID '
                                      f'by name "{pool_name}"! For more '
                                      f'details see syndicate logs.')
            elif provider_arns:
                for arn in provider_arns:
                    pool_id = arn.split('/')[-1]
                    _LOG.debug(f'Resolving ARN for Cognito User Pool by ID '
                               f'{pool_id}')
                    if self.cognito_res.is_user_pool_exists(pool_id):
                        new_provider_arns.append(arn)
                    else:
                        USER_LOG.warn(f'Cognito User Pool with ID {pool_id} '
                                      f'not found.')

            if new_provider_arns:
                _LOG.debug(f'Going to apply the next provider ARNs '
                           f'{new_provider_arns} to API Gateway '
                           f'{deep_get(openapi_context, ["info", "title"])}')
                authorizer[PROVIDER_ARNS_KEY] = new_provider_arns
            else:
                raise AssertionError(
                    f'Cognito User Pools can\'t be resolved by ' + 'names: '
                    f'{pools_names}' if pools_names else
                    f'ARNs: {provider_arns}')

    def get_lambda_permissions_for_api(self, lambda_arn, api_gateway_id):
        permissions = self.lambda_res.get_existing_permissions(lambda_arn)
        # Filter the permissions related to the specific API Gateway
        filtered_permissions = [
            statement for statement in permissions
            if deep_get(
                statement, SOURCE_ARN_DEEP_KEY, ""
            ).startswith('arn:aws:execute-api:') and api_gateway_id in deep_get(
                statement, SOURCE_ARN_DEEP_KEY, "")
        ]

        return filtered_permissions

    def create_lambdas_permissions(
        self,
        api_gateway_id: str,
        api_lambdas_arns: set[str],
        route: str
    ):

        api_source_arn = (f'arn:aws:execute-api:{self.region}:'
                          f'{self.account_id}:{api_gateway_id}{route}')
        for lambda_arn in api_lambdas_arns:
            _id = f'{lambda_arn}-{api_source_arn}'
            statement_id = md5(_id.encode('utf-8')).hexdigest()
            self.lambda_res.add_invocation_permission(
                name=lambda_arn,
                principal='apigateway.amazonaws.com',
                source_arn=api_source_arn,
                statement_id=statement_id,
                exists_ok=True
            )

    def remove_lambdas_permissions(self, api_gateway_id, api_lambdas_arns):
        for lambda_arn in api_lambdas_arns:
            existing_permissions = self.get_lambda_permissions_for_api(
                lambda_arn, api_gateway_id)

            existing_permissions = {
                deep_get(perm, SOURCE_ARN_DEEP_KEY): perm.get('Sid')
                for perm in existing_permissions
            }
            self.lambda_res.remove_permissions(lambda_arn,
                                               existing_permissions.values())

    @staticmethod
    def get_deploy_stage_name(stage_name=None):
        return stage_name if stage_name else 'prod'

    def __deploy_api_gateway(self, api_id, meta, api_resources):
        deploy_stage = self.get_deploy_stage_name(meta.get('deploy_stage'))
        cache_cluster_configuration = meta.get('cluster_cache_configuration')
        root_cache_enabled = cache_cluster_configuration.get(
            'cache_enabled') if cache_cluster_configuration else None
        cache_size = cache_cluster_configuration.get(
            'cache_size') if cache_cluster_configuration else None
        self.connection.deploy_api(api_id, stage_name=deploy_stage,
                                   cache_cluster_enabled=root_cache_enabled,
                                   cache_cluster_size=str(
                                       cache_size) if cache_size else None)
        throttling_cluster_configuration = meta.get(
            'cluster_throttling_configuration')
        throttling_enabled = throttling_cluster_configuration.get(
            'throttling_enabled') if throttling_cluster_configuration else None
        patch_operations = []
        if not throttling_enabled:
            patch_operations.append({
                'op': OPERATION_REPLACE,
                'path': '/*/*/throttling/rateLimit',
                'value': str(_DISABLE_THROTTLING_VALUE),
            })
            patch_operations.append({
                'op': OPERATION_REPLACE,
                'path': '/*/*/throttling/burstLimit',
                'value': str(_DISABLE_THROTTLING_VALUE),
            })
        # configure caching
        if root_cache_enabled:
            _LOG.debug('Cluster cache configuration found:{0}'.format(
                cache_cluster_configuration))
            # set default ttl for root endpoint
            cluster_cache_ttl_sec = cache_cluster_configuration.get(
                'cache_ttl_sec')
            encrypt_cache_data = cache_cluster_configuration.get(
                'encrypt_cache_data')
            if cluster_cache_ttl_sec is not None:
                patch_operations.append({
                    'op': OPERATION_REPLACE,
                    'path': '/*/*/caching/ttlInSeconds',
                    'value': str(cluster_cache_ttl_sec),
                })
            if encrypt_cache_data is not None:
                patch_operations.append({
                    'op': OPERATION_REPLACE,
                    'path': '/*/*/caching/dataEncrypted',
                    'value': 'true' if bool(encrypt_cache_data) else 'false'
                })
        # configure throttling
        if throttling_enabled:
            throttling_rate_limit = throttling_cluster_configuration.get(
                'throttling_rate_limit', API_GW_DEFAULT_THROTTLING_RATE_LIMIT)
            throttling_burst_limit = throttling_cluster_configuration.get(
                'throttling_burst_limit', API_GW_DEFAULT_THROTTLING_BURST_LIMIT)
            patch_operations.append({
                'op': OPERATION_REPLACE,
                'path': '/*/*/throttling/rateLimit',
                'value': str(throttling_rate_limit),
            })
            patch_operations.append({
                'op': OPERATION_REPLACE,
                'path': '/*/*/throttling/burstLimit',
                'value': str(throttling_burst_limit),
            })
        if any([root_cache_enabled, throttling_enabled]):
            self.connection.update_configuration(
                rest_api_id=api_id,
                stage_name=deploy_stage,
                patch_operations=patch_operations
            )
        # customize settings for endpoints
        self.configure_resources(api_id, deploy_stage, api_resources)

    def __prepare_api_resources_args(
            self, api_id, api_resources, api_resp=None,
            api_integration_resp=None,
            resources_statement_singleton: bool = False):
        # describe authorizers and create a mapping
        authorizers = self.connection.get_authorizers(api_id)
        authorizers_mapping = {x['name']: x['id'] for x in authorizers}
        args = []
        for each in api_resources:
            resource_meta = api_resources[each]
            _LOG.info('Creating resource %s ...', each)
            if each.startswith('/'):
                resource_id = self.connection.get_resource_id(api_id, each)
                if resource_id:
                    _LOG.info('Resource %s exists.', each)
                    enable_cors = resource_meta.get('enable_cors')
                    self._check_existing_methods(
                        api_id=api_id, resource_id=resource_id,
                        resource_path=each,
                        resource_meta=resource_meta,
                        enable_cors=enable_cors,
                        authorizers_mapping=authorizers_mapping,
                        api_resp=api_resp,
                        api_integration_resp=api_integration_resp,
                        resources_statement_singleton=resources_statement_singleton)
                else:
                    args.append({
                        'api_id': api_id,
                        'resource_path': each,
                        'resource_meta': resource_meta,
                        'authorizers_mapping': authorizers_mapping,
                        'resources_statement_singleton': resources_statement_singleton
                    })
            else:
                raise AssertionError(
                    "API resource must starts with '/', but found %s", each)
        return args

    def describe_api_resources(self, name, meta, api_id=None):
        if not api_id:
            api = self.connection.get_api_by_name(name)
            if not api:
                return
            api_id = api['id']

        response = self.connection.get_api(api_id)
        if not response:
            return
        response['resources'] = self.connection.get_resources(api_id)
        _LOG.info('Described %s API Gateway.', name)
        arn = 'arn:aws:apigateway:{0}::/restapis/{1}'.format(self.region,
                                                             api_id)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_openapi(self, api_id, stage_name):
        response = self.connection.describe_openapi(api_id, stage_name)
        return json.loads(response['body'].read().decode("utf-8")) \
            if isinstance(response, dict) else None

    def _check_existing_methods(self, api_id, resource_id, resource_path,
                                resource_meta,
                                enable_cors, authorizers_mapping,
                                api_resp=None,
                                api_integration_resp=None,
                                resources_statement_singleton: bool = False
                                ):
        """ Check if all specified methods exist and create some if not.
    
        :type api_id: str
        :type resource_id: str
        :type resource_meta: dict
        :type enable_cors: bool or None
        :type:
        """
        methods_statement_singleton = resource_meta.get(
            POLICY_STATEMENT_SINGLETON)
        for method in resource_meta:
            if method == 'enable_cors':
                continue
            if self.connection.get_method(api_id, resource_id, method):
                _LOG.info('Method %s exists.', method)
                continue
            else:
                _LOG.info('Creating method %s for resource %s...',
                          method, resource_id)
                self._create_method_from_metadata(
                    api_id=api_id,
                    resource_id=resource_id,
                    resource_path=resource_path,
                    method=method,
                    method_meta=resource_meta[method],
                    authorizers_mapping=authorizers_mapping,
                    api_resp=api_resp,
                    api_integration_resp=api_integration_resp,
                    enable_cors=enable_cors,
                    resources_statement_singleton=resources_statement_singleton,
                    methods_statement_singleton=methods_statement_singleton
                )
            if enable_cors and not self.connection.get_method(api_id,
                                                              resource_id,
                                                              'OPTIONS'):
                _LOG.info('Enabling CORS for resource %s...', resource_id)
                self.connection.enable_cors_for_resource(api_id, resource_id)

    @unpack_kwargs
    def _create_resource_from_metadata(self, api_id, resource_path,
                                       resource_meta,
                                       authorizers_mapping,
                                       resources_statement_singleton: bool = False):
        self.connection.create_resource(api_id, resource_path)
        _LOG.info('Resource %s created.', resource_path)
        resource_id = self.connection.get_resource_id(api_id, resource_path)
        enable_cors = resource_meta.get('enable_cors')
        methods_statement_singleton = resource_meta.get(
            POLICY_STATEMENT_SINGLETON)
        for method in resource_meta:
            try:
                if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                    continue

                method_meta = resource_meta[method]
                _LOG.info('Creating method %s for resource %s...',
                          method, resource_path)
                self._create_method_from_metadata(
                    api_id=api_id,
                    resource_id=resource_id,
                    resource_path=resource_path,
                    method=method,
                    method_meta=method_meta,
                    enable_cors=enable_cors,
                    authorizers_mapping=authorizers_mapping,
                    resources_statement_singleton=resources_statement_singleton,
                    methods_statement_singleton=methods_statement_singleton
                )
            except Exception as e:
                _LOG.error('Resource: {0}, method {1}.'
                           .format(resource_path, method), exc_info=True)
                raise e
            _LOG.info('Method %s for resource %s created.', method,
                      resource_path)
        # create enable cors only after all methods in resource created
        if enable_cors:
            self.connection.enable_cors_for_resource(api_id, resource_id)
            _LOG.info('CORS enabled for resource %s', resource_path)

    def _create_method_from_metadata(
            self, api_id, resource_id, resource_path, method, method_meta,
            authorizers_mapping, enable_cors=False, api_resp=None,
            api_integration_resp=None,
            resources_statement_singleton: bool = False,
            methods_statement_singleton: bool = False):
        resources_statement_singleton = resources_statement_singleton or False
        methods_statement_singleton = methods_statement_singleton or False
        # init responses for method
        resp = self.init_method_responses(api_resp, method_meta)

        # init integration responses for method
        integr_resp = self.init_integration_method_responses(
            api_integration_resp, method_meta)

        # resolve authorizer if needed
        authorization_type = method_meta.get('authorization_type')
        if authorization_type not in ['NONE', 'AWS_IAM']:
            # type is authorizer, so add id to meta
            authorizer_id = authorizers_mapping.get(authorization_type)
            if not authorizer_id:
                raise AssertionError(
                    'Authorizer {0} does not exist'.format(authorization_type))
            method_meta['authorizer_id'] = authorizer_id
            authorizer = self.connection.get_authorizer(
                api_id, authorizer_id).get('type')
            if authorizer == _COGNITO_AUTHORIZER_TYPE:
                authorization_type = _COGNITO_AUTHORIZER_TYPE
            else:
                authorization_type = _CUSTOM_AUTHORIZER_TYPE

        method_request_models = method_meta.get('method_request_models')
        if method_request_models:
            (content_type, name), = method_request_models.items()
            model = self.connection.get_model(api_id, name)
            method_request_models = model if not model else method_request_models

        request_validator_id = self._retrieve_request_validator_id(
            api_id, method_meta.get('request_validator'))

        self.connection.create_method(
            api_id, resource_id, method,
            authorization_type=authorization_type,
            authorizer_id=method_meta.get('authorizer_id'),
            api_key_required=method_meta.get('api_key_required'),
            request_parameters=method_meta.get('method_request_parameters'),
            request_models=method_request_models,
            request_validator=request_validator_id)
        # second step: create integration
        integration_type = method_meta.get('integration_type')
        # set up integration - lambda or aws service
        body_template = method_meta.get('integration_request_body_template')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior')
        request_parameters = method_meta.get('integration_request_parameters')
        # TODO split to map - func implementation
        if integration_type:
            if integration_type == 'lambda':
                lambda_name = method_meta['lambda_name']
                # alias has a higher priority than version in arn resolving
                lambda_version = method_meta.get('lambda_version')
                lambda_alias = method_meta.get('lambda_alias')
                lambda_arn = self.lambda_res. \
                    resolve_lambda_arn_by_version_and_alias(lambda_name,
                                                            lambda_version,
                                                            lambda_alias)
                enable_proxy = method_meta.get('enable_proxy')
                cache_configuration = method_meta.get('cache_configuration')
                cache_key_parameters = cache_configuration.get(
                    'cache_key_parameters') if cache_configuration else None
                self.connection.create_lambda_integration(
                    lambda_arn, api_id, resource_id, method, body_template,
                    passthrough_behavior, method_meta.get('lambda_region'),
                    enable_proxy=enable_proxy,
                    cache_key_parameters=cache_key_parameters,
                    request_parameters=request_parameters)
                # add permissions to invoke
                # Allows to apply method or resource singleton of a policy
                # statement, setting wildcard on the respective scope.

                api_source_arn = f"arn:aws:execute-api:{self.region}:" \
                                 f"{self.account_id}:{api_id}/*" \
                                 "/{method}/{path}"

                _method, _path = method, resource_path.lstrip('/')
                if resources_statement_singleton:
                    _path = '*'
                if methods_statement_singleton:
                    _method = '*'

                api_source_arn = api_source_arn.format(
                    method=_method, path=_path
                )
                _id = f'{lambda_arn}-{api_source_arn}'
                statement_id = md5(_id.encode('utf-8')).hexdigest()
                response: dict = self.lambda_res.add_invocation_permission(
                    name=lambda_arn,
                    principal='apigateway.amazonaws.com',
                    source_arn=api_source_arn,
                    statement_id=statement_id,
                    exists_ok=True
                )
                if response is None:
                    message = f'Permission: \'{statement_id}\' attached to ' \
                              f'\'{lambda_arn}\' lambda to allow ' \
                              f'lambda:InvokeFunction for ' \
                              f'apigateway.amazonaws.com principal from ' \
                              f'\'{api_source_arn}\' SourceArn already exists.'
                    _LOG.warning(message + ' Skipping.')

            elif integration_type == 'service':
                uri = method_meta.get('uri')
                role = method_meta.get('role')
                integration_method = method_meta.get('integration_method')
                self.connection.create_service_integration(self.account_id,
                                                           api_id,
                                                           resource_id,
                                                           method,
                                                           integration_method,
                                                           role, uri,
                                                           body_template,
                                                           passthrough_behavior,
                                                           request_parameters)
            elif integration_type == 'mock':
                self.connection.create_mock_integration(api_id, resource_id,
                                                        method,
                                                        body_template,
                                                        passthrough_behavior)
            elif integration_type == 'http':
                integration_method = method_meta.get('integration_method')
                uri = method_meta.get('uri')
                enable_proxy = method_meta.get('enable_proxy')
                self.connection.create_http_integration(api_id, resource_id,
                                                        method,
                                                        integration_method,
                                                        uri,
                                                        body_template,
                                                        passthrough_behavior,
                                                        enable_proxy)
            else:
                raise AssertionError('%s integration type does not exist.',
                                     integration_type)
        # third step: setup method responses
        if resp:
            for response in resp:
                self.connection.create_method_response(
                    api_id, resource_id, method, response.get('status_code'),
                    response.get('response_parameters'),
                    response.get('response_models'), enable_cors)
        else:
            self.connection.create_method_response(
                api_id, resource_id, method, enable_cors=enable_cors)
        # fourth step: setup integration responses
        if integr_resp:
            for each in integr_resp:
                self.connection.create_integration_response(
                    api_id, resource_id, method, each.get('status_code'),
                    each.get('error_regex'),
                    each.get('response_parameters'),
                    each.get('response_templates'), enable_cors)
        else:
            self.connection.create_integration_response(
                api_id, resource_id, method, enable_cors=enable_cors)

    @staticmethod
    def init_method_responses(api_resp, method_meta):
        method_responses = method_meta.get("responses")
        if method_responses:
            resp = method_responses
        elif api_resp:
            resp = api_resp
        else:
            resp = []
        return resp

    @staticmethod
    def init_integration_method_responses(api_integration_resp,
                                          method_meta):
        integration_method_responses = method_meta.get("integration_responses")
        if integration_method_responses:
            integration_resp = integration_method_responses
        elif api_integration_resp:
            integration_resp = api_integration_resp
        else:
            integration_resp = []
        return integration_resp

    def _customize_gateway_responses(self, api_id):
        responses = self.connection.get_gateway_responses(api_id)
        response_types = [r['responseType'] for r in responses]
        for response_type in response_types:
            time.sleep(10)
            self.connection.add_header_to_gateway_response(api_id,
                                                           response_type,
                                                           _CORS_HEADER_NAME,
                                                           _CORS_HEADER_VALUE)

    @staticmethod
    def _get_lambdas_invoked_by_api_gw(resources_meta, retrieve_aliases=False):
        lambdas = set()
        for resource, meta in resources_meta.items():
            for method, description in meta.items():
                if method in SUPPORTED_METHODS:
                    lambda_ = description.get('lambda_name')
                    if lambda_:
                        if retrieve_aliases:
                            lambda_ = (lambda_,
                                       description.get('lambda_alias'))
                        lambdas.add(lambda_)
        return list(lambdas)

    def remove_api_gateways(self, args):
        for arg in args:
            self._remove_api_gateway(**arg)
            # wait for success deletion
            time.sleep(60)

    def _remove_invocation_permissions_from_lambdas(self, config):
        api_id = config['description']['id']
        _LOG.info(fr'Removing invocation permissions for api {api_id}')
        lambdas_aliases = self._get_lambdas_invoked_by_api_gw(
            config['resource_meta'].get('resources', {}),
            retrieve_aliases=True)
        for lambda_, alias in lambdas_aliases:
            _LOG.info(f'Removing invocation permissions for api {api_id} '
                      f'from lambda {lambda_} and alias {alias}')
            statements = self.lambda_res.get_invocation_permission(
                lambda_name=self.lambda_res.build_lambda_arn(lambda_),
                qualifier=alias
            ).get('Statement', [])
            ids_to_remove = [st.get('Sid') for st in statements if
                             api_id in st.get('Condition', {}).get(
                                 'ArnLike', {}).get('AWS:SourceArn', '')]
            self.lambda_res.remove_invocation_permissions(
                lambda_name=lambda_, qualifier=alias,
                ids_to_remove=ids_to_remove
            )

    def _remove_api_gateway(self, arn, config):
        api_id = config['description']['id']
        stage_name = config["resource_meta"]["deploy_stage"]
        openapi_context = self.describe_openapi(api_id, stage_name)
        if openapi_context:
            api_lambdas_arns = self.extract_api_gateway_lambdas_arns(
                openapi_context)
            api_lambda_auth_arns = self.extract_api_gateway_lambda_auth_arns(
                openapi_context)
            self.remove_lambdas_permissions(
                api_id,
                {*api_lambdas_arns, *api_lambda_auth_arns}
            )
        try:
            if self.connection.get_api(api_id):
                self.connection.remove_api(api_id)
                _LOG.info(f'API Gateway {api_id} was removed.')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                _LOG.warning(f'API Gateway {api_id} is not found')
            else:
                raise e

    @unpack_kwargs
    def _create_model_from_metadata(self, api_id, models):
        _LOG.info('Going to process API Gateway models')
        for name, model_data in models.items():
            description = model_data.get('description')
            schema = model_data.get('schema')
            if isinstance(schema, dict):
                schema = json.dumps(schema)
            content_type = model_data.get('content_type')
            self.connection.create_model(
                api_id, name, content_type, description, schema)

    def build_web_socket_api_gateway_arn(self, api_id: str) -> str:
        return f'arn:aws:execute-api:{self.apigw_v2.client.meta.region_name}' \
               f':{self.account_id}:{api_id}/*'

    def create_web_socket_api_gateway(self, args):
        return self.create_pool(self._create_web_socket_api_from_meta, args, 1)

    @unpack_kwargs
    def _create_web_socket_api_from_meta(self, name: str, meta: dict):
        stage_name = meta.get('deploy_stage')
        resources = meta.get('resources') or {}
        route_selection_expression = meta.get('route_selection_expression')
        api_id = self.apigw_v2.create_web_socket_api(
            name=name, route_selection_expression=route_selection_expression,
            tags=meta.get('tags'))
        for route_name, route_meta in resources.items():
            int_type = route_meta.get('integration_type') or 'lambda'
            if int_type != 'lambda':
                _LOG.error(f'Integration type: {int_type} currently '
                           f'not supported. Skipping..')
                continue
            lambda_name = route_meta['lambda_name']
            lambda_version = route_meta.get('lambda_version')
            lambda_alias = route_meta.get('lambda_alias')
            lambda_arn = self.lambda_res.resolve_lambda_arn_by_version_and_alias(
                lambda_name, lambda_version, lambda_alias)

            integration_id = self.apigw_v2.create_lambda_integration(
                api_id=api_id,
                lambda_arn=lambda_arn,
                enable_proxy=route_meta.get('enable_proxy') or False
            )
            self.apigw_v2.put_route_integration(
                api_id=api_id,
                route_name=route_name,
                integration_id=integration_id
            )
            source_arn = f'{self.build_web_socket_api_gateway_arn(api_id)}/{route_name}'

            self.lambda_res.add_invocation_permission(
                name=lambda_arn,
                principal='apigateway.amazonaws.com',
                source_arn=source_arn,
                statement_id=f'{name}-{route_name.strip("$")}-invoke',
                exists_ok=True
            )

        self.apigw_v2.create_stage(api_id=api_id, stage_name=stage_name)
        return self.describe_v2_api_gateway(
            name=name, meta=meta, api_id=api_id
        )

    def describe_v2_api_gateway(self, name, meta, api_id=None):
        if not api_id:
            api = self.apigw_v2.get_api_by_name(name)
            if not api:
                return
            api_id = api['ApiId']

        # response = self.connection.get_api(api_id)
        response = {'ApiId': api_id}
        # maybe the arn is not valid - I didn't manage to find a valid
        # example browsing for 5 minutes, so the hell with it. Currently,
        # nothing depends on it
        arn = self.build_web_socket_api_gateway_arn(api_id)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def remove_v2_api_gateway(self, args):
        for arg in args:
            self._remove_v2_api_gateway(**arg)
            # wait for success deletion
            # time.sleep(60)

    def _remove_v2_api_gateway(self, arn, config):
        api_id = config.get('description', {}).get('ApiId')
        if not api_id:
            _LOG.warning('V2 api id not found in output. Skipping')
            return

        lambda_arns = []
        routes = self.apigw_v2.get_routes(api_id)
        for route in routes['Items']:
            lambda_arns.append(self.apigw_v2.get_integration(
                api_id, route['Target'].replace('integrations/', '')))

        self.remove_lambdas_permissions(
            api_id, {*[arn for arn in lambda_arns if arn is not None]})
        self.apigw_v2.delete_api(api_id)
        return

    @staticmethod
    def extract_api_gateway_lambdas_arns(openapi_spec):
        api_gateway_lambdas_arns = {*()}

        for path, path_item in openapi_spec.get('paths', {}).items():
            for method, method_data in path_item.items():
                integration = method_data.get('x-amazon-apigateway-integration')
                if not integration or not integration.get('uri'):
                    continue
                uri = integration.get('uri')
                try:
                    lambda_arn = uri.split('/functions/')[1].split('/')[0]
                except IndexError:
                    _LOG.warning(f"Invalid lambda arn in integration uri {uri}")
                    continue

                api_gateway_lambdas_arns.add(lambda_arn)
        return api_gateway_lambdas_arns

    @staticmethod
    def extract_api_gateway_lambda_auth_arns(openapi_spec):
        api_gateway_lambdas_arns = {*()}

        security_schemas = deep_get(openapi_spec, SECURITY_SCHEMAS_DEEP_KEY, {})
        for schema_data in security_schemas.values():
            authorizer = schema_data.get("x-amazon-apigateway-authorizer")
            if not authorizer or not authorizer.get("authorizerUri"):
                continue
            uri = authorizer.get("authorizerUri")
            try:
                lambda_arn = uri.split('/functions/')[1].split('/')[0]
            except IndexError:
                _LOG.warning(f"Invalid lambda arn in authorizer uri {uri}")
                continue

            api_gateway_lambdas_arns.add(lambda_arn)
        return api_gateway_lambdas_arns
