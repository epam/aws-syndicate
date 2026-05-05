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
from syndicate.exceptions import ResourceNotFoundError, \
    InvalidValueError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection import LogsConnection
from syndicate.core.constants import (
    SOURCE_ARN_DEEP_KEY, SECURITY_SCHEMAS_DEEP_KEY,
    API_GW_DEFAULT_THROTTLING_RATE_LIMIT,
    API_GW_DEFAULT_THROTTLING_BURST_LIMIT,
    AUTHORIZATION_SCOPES_KEY
)
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
from syndicate.connection.api_gateway_connection import ApiGatewayV2Connection, \
    ApiGatewayConnection
from syndicate.core.resources.lambda_resource import LambdaResource

API_REQUIRED_PARAMS = ['resources', 'deploy_stage']

_LOG = get_logger(__name__)
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
                 cw_logs_conn: LogsConnection,
                 lambda_res: LambdaResource,
                 cognito_res, account_id, region) -> None:
        self.connection = apigw_conn
        self.lambda_res = lambda_res
        self.cognito_res = cognito_res
        self.account_id = account_id
        self.region = region
        self.apigw_v2 = apigw_v2_conn
        self.cw_logs_conn = cw_logs_conn

    def _create_default_validators(self, api_id):
        for name, options in _REQUEST_VALIDATORS.items():
            _id = self.connection.create_request_validator(
                api_id, name, options['validate_request_body'],
                options['validate_request_parameters']
            )
            options['id'] = _id

    def _sync_authorizers_from_meta(self, api_id: str, meta: dict) -> None:
        """
        Create or update REST API authorizers from meta.
        """
        authorizers = meta.get('authorizers') or {}
        if not authorizers:
            return
        by_name = {
            a['name']: a for a in self.connection.get_authorizers(api_id)
        }
        for key, val in authorizers.items():
            uri = None
            provider_arns = []
            if val.get('type') == _COGNITO_AUTHORIZER_TYPE:
                for pool in val.get('user_pools') or []:
                    user_pool_id = self.cognito_res.get_user_pool_id(pool)
                    if not user_pool_id and self.cognito_res.is_user_pool_exists(
                            pool):
                        user_pool_id = pool
                    if user_pool_id:
                        provider_arns.append(
                            f'arn:aws:cognito-idp:{self.region}:'
                            f'{self.account_id}:userpool/{user_pool_id}')
                    else:
                        USER_LOG.warn(
                            f'Authorizer \'{key}\': Cognito user pool '
                            f'{pool!r} was not found by name or as a pool id '
                            f'in {self.region}.')
            else:
                lambda_version = val.get('lambda_version')
                lambda_name = val.get('lambda_name')
                lambda_alias = val.get('lambda_alias')
                lambda_arn = self.lambda_res. \
                    resolve_lambda_arn_by_version_and_alias(lambda_name,
                                                            lambda_version,
                                                            lambda_alias)
                if not lambda_arn:
                    raise ResourceNotFoundError(
                        f'Authorizer \'{key}\': Lambda \'{lambda_name}\' not '
                        f'found (version={lambda_version!r}, '
                        f'alias={lambda_alias!r})'
                    )
                uri = (
                    f'arn:aws:apigateway:{self.region}:lambda:path/'
                    f'2015-03-31/functions/{lambda_arn}/invocations'
                )
                api_source_arn = (
                    f'arn:aws:execute-api:{self.region}:'
                    f'{self.account_id}:{api_id}/*/*'
                )
                self.lambda_res.add_invocation_permission(
                    statement_id=api_id,
                    name=lambda_arn,
                    source_arn=api_source_arn,
                    principal='apigateway.amazonaws.com'
                )

            # not found cognito user pool in region
            if val.get('type') == _COGNITO_AUTHORIZER_TYPE and not provider_arns:
                raise ResourceNotFoundError(
                    f'Authorizer \'{key}\': COGNITO_USER_POOLS requires at '
                    f'least one resolved user pool that exist in {self.region}'
                )

            existing = by_name.get(key)
            if existing:
                if val.get('type') == _COGNITO_AUTHORIZER_TYPE:
                    self.connection.update_cognito_authorizer_user_pools(
                        api_id=api_id,
                        authorizer_id=existing['id'],
                        provider_arns=provider_arns,
                        identity_source=val.get('identity_source'),
                        ttl=val.get('ttl'),
                    )
                else:
                    self.connection.update_authorizer(
                        api_id=api_id,
                        authorizer_id=existing['id'],
                        authorizer_uri=uri,
                        identity_source=val.get('identity_source'),
                        ttl=val.get('ttl'),
                    )
            else:
                self.connection.create_authorizer(
                    api_id=api_id, name=key,
                    type=val['type'],
                    authorizer_uri=uri,
                    identity_source=val.get('identity_source'),
                    ttl=val.get('ttl'),
                    provider_arns=provider_arns)

    def _sync_models_from_meta(self, api_id: str, meta: dict) -> None:
        """
        Create or update API Gateway models from meta
        """
        models = meta.get('models') or {}
        if not models:
            return

        _LOG.info('Syncing API Gateway models')
        for name, model_data in models.items():
            description = model_data.get('description')
            schema = model_data.get('schema')
            schema_arg = schema
            if isinstance(schema, dict):
                schema_arg = json.dumps(schema)
            content_type = model_data.get('content_type')
            existing = self.connection.get_model(api_id, name)
            if existing is None:
                self.connection.create_model(
                    api_id, name, content_type, description, schema_arg)
            else:
                self.connection.update_model(
                    api_id, name,
                    description=description,
                    schema=schema_arg,
                )

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

    def update_api_gateway(self, args):
        return self.create_pool(self._update_api_gateway_from_meta, args, 1)

    def update_api_gateway_openapi(self, args):
        return self.create_pool(self._update_api_gateway_openapi_from_meta, args, 1)

    def _escape_path(self, parameter):
        index = parameter.find('/', 0)
        if index == -1:
            return parameter
        parameter = parameter[:index] + '~1' + parameter[index + 1:]
        return self._escape_path(parameter)

    @staticmethod
    def _api_path_segment_count(path: str) -> int:
        return len([p for p in path.split('/') if p])

    @staticmethod
    def _enable_cors_active(resource_meta: dict) -> bool:
        enable_cors = resource_meta.get('enable_cors')
        if isinstance(enable_cors, bool):
            return enable_cors
        if isinstance(enable_cors, dict):
            return bool(enable_cors.get('state'))
        return False

    def _desired_http_methods_from_resource_meta(
            self,
            resource_meta: dict
    ) -> set:
        methods = {k for k in resource_meta if k in SUPPORTED_METHODS}
        if self._enable_cors_active(resource_meta):
            methods.add('OPTIONS')
        return methods

    @staticmethod
    def _path_required_as_meta_ancestor(path: str, meta_paths: set) -> bool:
        if path == '/':
            return True
        prefix = path.rstrip('/') + '/' if path != '/' else '/'
        for mp in meta_paths:
            if mp != path and mp.startswith(prefix):
                return True
        return False

    def _should_prune_whole_resource(self, path: str, meta_paths: set) -> bool:
        if path == '/':
            return False
        if path in meta_paths:
            return False
        if self._path_required_as_meta_ancestor(path, meta_paths):
            return False
        return True

    def _prune_absent_api_gateway_resources(
            self, api_id: str, meta_api_resources: dict) -> None:
        """Drop REST paths and HTTP methods in AWS that are not in meta.

        Called on every REST API update and continue-deploy so the API matches
        ``resources`` declaratively. Parent path segments without their own
        meta entry are kept when a descendant path is still in meta.
        Removals run deepest-first. Existing methods listed in meta are not
        modified here (only extras are deleted).
        """
        meta_paths = set(meta_api_resources.keys())
        aws_resources = self.connection.get_resources(api_id)
        id_by_path = {r['path']: r['id'] for r in aws_resources}
        paths_to_remove = [
            r['path'] for r in aws_resources
            if self._should_prune_whole_resource(r['path'], meta_paths)
        ]
        paths_to_remove.sort(
            key=self._api_path_segment_count, reverse=True)
        for path in paths_to_remove:
            rid = id_by_path.get(path)
            if not rid:
                continue
            _LOG.info(f'Pruning API Gateway resource absent from meta: {path}')
            self.connection.delete_resource(api_id, rid)

        for path, resource_meta in meta_api_resources.items():
            resource_id = self.connection.get_resource_id(api_id, path)
            if not resource_id:
                continue
            detail = self.connection.get_resource(api_id, resource_id)
            existing_methods = detail.get('resourceMethods') or {}
            desired = self._desired_http_methods_from_resource_meta(
                resource_meta)
            for http_method in list(existing_methods.keys()):
                if http_method not in desired:
                    _LOG.info(
                        f'Pruning API Gateway method absent from meta: '
                        f'{http_method} {path}'
                    )
                    self.connection.delete_method(
                        api_id, resource_id, http_method
                    )

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

                        log_config = method_meta.get('logging_configuration')
                        if isinstance(log_config, dict):
                            logging_enabled = log_config.get('logging_enabled')
                        else:
                            logging_enabled = False
                        if logging_enabled:
                            _LOG.info(
                                f'Configuring logging for {resource_path};'
                                f'log_level: '
                                f"{log_config.get('log_level', 'ERROR')};"
                                f'data_tracing: '
                                f"{log_config.get('data_tracing', False)};"
                                f'detailed_metrics: '
                                f"{log_config.get('detailed_metrics', False)}"
                            )
                            patch_operations.append({
                                'op': OPERATION_REPLACE,
                                'path': f'/{escaped_resource}/{method}/'
                                        f'logging/loglevel',
                                'value': log_config.get('log_level', 'ERROR'),
                            })
                            if log_config.get('data_tracing'):
                                patch_operations.append({
                                    'op': OPERATION_REPLACE,
                                    'path': f'/{escaped_resource}/{method}/'
                                            f'logging/dataTrace',
                                    'value': 'true',
                                })
                            if log_config.get('detailed_metrics'):
                                patch_operations.append({
                                    'op': OPERATION_REPLACE,
                                    'path': f'/{escaped_resource}/{method}/'
                                            f'metrics/enabled',
                                    'value': 'true',
                                })

                    if patch_operations:
                        self.connection.update_configuration(
                            rest_api_id=api_id,
                            stage_name=stage_name,
                            patch_operations=patch_operations
                        )
                    _LOG.info(f'Resource {resource_path} was configured')

    @unpack_kwargs
    def _create_api_gateway_from_meta(self, name: str, meta: dict):
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

        self._sync_authorizers_from_meta(api_id, meta)
        self._sync_models_from_meta(api_id, meta)
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
    def _update_api_gateway_from_meta(
            self,
            name: str,
            meta: dict,
            context=None
    ):
        validate_params(name, meta, API_REQUIRED_PARAMS)
        _LOG.info(f'Updating API Gateway \'{name}\'')

        api_id = self.connection.get_api_id(name)
        if not api_id:
            raise ResourceNotFoundError(
                f'API Gateway \'{name}\' not found. Cannot update.'
            )

        self._sync_authorizers_from_meta(api_id, meta)
        self._sync_models_from_meta(api_id, meta)

        meta_api_resources = meta['resources']
        resources_statement_singleton = meta.get(POLICY_STATEMENT_SINGLETON)
        api_resp = meta.get('api_method_responses')
        api_integration_resp = meta.get('api_method_integration_responses')

        # Declarative sync: remove paths/methods missing from meta first.
        self._prune_absent_api_gateway_resources(api_id, meta_api_resources)

        args = self.__prepare_api_resources_args(
            api_id=api_id,
            api_resources=meta_api_resources,
            api_resp=api_resp,
            api_integration_resp=api_integration_resp,
            resources_statement_singleton=resources_statement_singleton
        )
        if args:
            _LOG.debug(f'Creating new API Gateway paths on {api_id}')
            self.create_pool(self._create_resource_from_metadata, args, 1)
            time.sleep(10)

        minimum_compression_size = meta.get('minimum_compression_size', None)
        if not minimum_compression_size:
            _LOG.debug("No minimal_compression_size param - "
                       "compression isn't enabled")
        self.connection.update_compression_size(
            rest_api_id=api_id,
            compression_size=minimum_compression_size)

        _LOG.debug(f'Deploying API Gateway {api_id}')
        self.__deploy_api_gateway(api_id, meta, meta_api_resources)
        return self.describe_api_resources(api_id=api_id, meta=meta,
                                           name=name)

    @unpack_kwargs
    def _create_api_gateway_openapi_from_meta(self, name: str, meta: dict):
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
    def _update_api_gateway_openapi_from_meta(
            self,
            name: str,
            meta: dict,
            context
    ):
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
                raise ResourceNotFoundError(
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

            try:
                existing_permissions = self.get_lambda_permissions_for_api(
                    lambda_arn, api_gateway_id)

                existing_permissions = {
                    deep_get(perm, SOURCE_ARN_DEEP_KEY): perm.get('Sid')
                    for perm in existing_permissions
                }
                self.lambda_res.remove_permissions(lambda_arn,
                                                   existing_permissions.values())
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'AccessDeniedException':
                    _LOG.warning(
                        f"Cannot remove permissions from Lambda "
                        f"'{lambda_arn}': access denied "
                        f"(cross-account). Skipping.")
                    continue
                raise


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

        patch_operations = []
        throttling_cluster_configuration = meta.get(
            'cluster_throttling_configuration')
        throttling_enabled = throttling_cluster_configuration.get(
            'throttling_enabled') if throttling_cluster_configuration else None
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
            _LOG.debug(
                f'Cluster cache configuration found: '
                f'{cache_cluster_configuration}'
            )
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

        # configure logging
        log_config = meta.get('logging_configuration')
        logging_enabled = log_config.get('logging_enabled') if (
            isinstance(log_config, dict)) else False
        if logging_enabled:
            patch_operations.append({
                'op': OPERATION_REPLACE,
                'path': '/*/*/logging/loglevel',
                'value': log_config.get('log_level', 'ERROR'),
            })
            if log_config.get('data_tracing'):
                patch_operations.append({
                    'op': OPERATION_REPLACE,
                    'path': '/*/*/logging/dataTrace',
                    'value': 'true',
                })
            if log_config.get('detailed_metrics'):
                patch_operations.append({
                    'op': OPERATION_REPLACE,
                    'path': '/*/*/metrics/enabled',
                    'value': 'true',
                })

        if any([root_cache_enabled, throttling_enabled, logging_enabled]):
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
                    self._check_existing_methods(
                        api_id=api_id, resource_id=resource_id,
                        resource_path=each,
                        resource_meta=resource_meta,
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
                raise InvalidValueError(
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
            return {}
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

    def describe_tags(self, api_arn: str) -> dict | None:
        tag_response = self.connection.describe_tags(api_arn=api_arn)
        tags = tag_response.get('tags', {})
        return tags

    def _check_existing_methods(
            self,
            api_id: str,
            resource_id: str,
            resource_path: str,
            resource_meta: dict,
            authorizers_mapping: dict,
            api_resp: list = None,
            api_integration_resp: list =None,
            resources_statement_singleton: bool = False
    ):
        """
        Create missing HTTP methods or re-apply meta for existing ones.

        New methods use ``put_method``; existing methods are updated with
        ``update_method`` patches, ``update_integration`` (patch or
        ``put_integration`` when required), and responses match meta.
        """
        methods_statement_singleton = resource_meta.get(
            POLICY_STATEMENT_SINGLETON)
        enable_cors = resource_meta.get('enable_cors')
        if isinstance(enable_cors, bool):
            USER_LOG.warning(
                'Deprecated parameter "enable_cors" format. '
                'Please check the documentation for more details.')
            enable_cors = {'state': True} if enable_cors else {'state': False}
        if not enable_cors:
            enable_cors = {'state': False}

        for method in resource_meta:
            if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                continue
            method_exists = bool(self.connection.get_method(
                api_id, resource_id, method))
            if method_exists:
                _LOG.info(
                    'Method %s exists on %s — syncing configuration from meta.',
                    method, resource_path)
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
                methods_statement_singleton=methods_statement_singleton,
                method_already_exists=method_exists,
            )
        if enable_cors.get('state'):
            _LOG.info(f'Syncing CORS for resource {resource_path}...')
            self.connection.enable_cors_for_resource(
                api_id, resource_id, enable_cors
            )

    @unpack_kwargs
    def _create_resource_from_metadata(self, api_id, resource_path,
                                       resource_meta,
                                       authorizers_mapping,
                                       resources_statement_singleton: bool = False):
        self.connection.create_resource(api_id, resource_path)
        _LOG.info(f'Resource {resource_path} created.')
        resource_id = self.connection.get_resource_id(api_id, resource_path)
        methods_statement_singleton = resource_meta.get(
            POLICY_STATEMENT_SINGLETON)
        enable_cors = resource_meta.get('enable_cors')
        if isinstance(enable_cors, bool):
            USER_LOG.warning(
                'Deprecated parameter "enable_cors" format. '
                'Please check the documentation for more details.')
            if enable_cors:
                enable_cors = {
                    'state': True
                }
            else:
                enable_cors = {
                    'state': False
                }

        for method in resource_meta:
            try:
                if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                    continue

                method_meta = resource_meta[method]
                _LOG.info(f'Creating method {method} for resource '
                          f'{resource_path}...',)
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
                _LOG.error(f'Resource: {resource_path}, method {method}.',
                           exc_info=True)
                raise e
            _LOG.info(f'Method {method} for resource {resource_path} created.')
        # create enable cors only after all methods in resource created
        if enable_cors.get('state'):
            self.connection.enable_cors_for_resource(
                api_id, resource_id, enable_cors)
            _LOG.info(f'CORS enabled for resource {resource_path}')

    def _create_method_from_metadata(
            self, api_id, resource_id, resource_path, method, method_meta,
            authorizers_mapping,
            enable_cors: dict = None,
            api_resp=None,
            api_integration_resp=None,
            resources_statement_singleton: bool = False,
            methods_statement_singleton: bool = False,
            method_already_exists: bool = False
    ):
        resources_statement_singleton = resources_statement_singleton or False
        methods_statement_singleton = methods_statement_singleton or False
        # init responses for method
        resp = self.init_method_responses(api_resp, method_meta)

        # init integration responses for method
        integr_resp = self.init_integration_method_responses(
            api_integration_resp, method_meta)

        # resolve authorizer if needed
        authorization_type = method_meta.get('authorization_type')
        authorization_scopes = None
        if authorization_type not in ['NONE', 'AWS_IAM']:
            authorizer_id = authorizers_mapping.get(authorization_type)
            if not authorizer_id:
                raise ResourceNotFoundError(
                    'Authorizer {0} does not exist'.format(authorization_type))
            method_meta['authorizer_id'] = authorizer_id
            authorizer = self.connection.get_authorizer(
                api_id, authorizer_id).get('type')
            if authorizer == _COGNITO_AUTHORIZER_TYPE:
                authorization_type = _COGNITO_AUTHORIZER_TYPE
                authorization_scopes = method_meta.get(AUTHORIZATION_SCOPES_KEY)
            else:
                authorization_type = _CUSTOM_AUTHORIZER_TYPE
                if method_meta.get(AUTHORIZATION_SCOPES_KEY):
                    raise InvalidValueError(
                        f"'authorization_scopes' can only be used with "
                        f"COGNITO_USER_POOLS authorizer type, but "
                        f"authorizer '{method_meta.get('authorization_type')}' "
                        f"is of type '{authorizer}'."
                    )
        else:
             if method_meta.get(AUTHORIZATION_SCOPES_KEY):
                raise InvalidValueError(
                    f"'authorization_scopes' can only be used with "
                    f"COGNITO_USER_POOLS authorizer type, but "
                    f"authorization_type is '{authorization_type}'."
                )

        method_request_models = method_meta.get('method_request_models')
        if method_request_models:
            (content_type, name), = method_request_models.items()
            model = self.connection.get_model(api_id, name)
            method_request_models = model if not model else method_request_models

        request_validator_id = self._retrieve_request_validator_id(
            api_id, method_meta.get('request_validator'))

        if method_already_exists:
            self.connection.update_method_configuration(
                api_id=api_id,
                resource_id=resource_id,
                http_method=method,
                authorization_type=authorization_type,
                authorizer_id=method_meta.get('authorizer_id'),
                api_key_required=method_meta.get('api_key_required'),
                request_parameters=method_meta.get('method_request_parameters'),
                request_models=method_request_models,
                request_validator_id=request_validator_id,
                authorization_scopes=authorization_scopes
            )
        else:
            self.connection.create_method(
                api_id, resource_id, method,
                authorization_type=authorization_type,
                authorizer_id=method_meta.get('authorizer_id'),
                api_key_required=method_meta.get('api_key_required'),
                request_parameters=method_meta.get('method_request_parameters'),
                request_models=method_request_models,
                request_validator=request_validator_id,
                authorization_scopes=authorization_scopes
            )
        integration_configured = False
        # second step: create integration
        integration_type = method_meta.get('integration_type')
        if integration_type:
            integration_type = integration_type.lower()
        # set up integration - lambda or aws service
        body_template = method_meta.get('integration_request_body_template')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior'
        )
        credentials = method_meta.get('credentials')
        request_parameters = method_meta.get('integration_request_parameters')
        existing_integration = (
            method_already_exists
            and integration_type
            and self.connection.get_rest_integration(
                api_id, resource_id, method)
        )
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
                if not lambda_arn:
                    USER_LOG.warning(
                        'Lambda %r was not found; lambda_version=%r, '
                        'lambda_alias=%r.\n'
                        'A temporary MOCK integration (HTTP 200, empty body) '
                        'was attached for %s %s. '
                        'Fix \'lambda_name\' in deployment resources '
                        'and re-deploy to connect the real Lambda',
                        lambda_name, lambda_version, lambda_alias,
                        method, resource_path
                    )
                    mock_templates = {
                        'application/json': '{"statusCode": 200}',
                    }
                    mock_pb = passthrough_behavior or 'WHEN_NO_MATCH'
                    if existing_integration:
                        self.connection.update_integration_configuration(
                            api_id, resource_id, method,
                            int_type='MOCK',
                            request_templates=mock_templates,
                            passthrough_behavior=mock_pb,
                        )
                    else:
                        self.connection.create_mock_integration(
                            api_id, resource_id, method,
                            request_templates=mock_templates,
                            passthrough_behavior=mock_pb,
                        )
                    integration_configured = True
                else:
                    enable_proxy = method_meta.get('enable_proxy')
                    if enable_proxy and body_template:
                        USER_LOG.warning(
                            'integration_request_body_template is not applied '
                            'for %s %s when enable_proxy is true. Set '
                            'enable_proxy to false to use mapping templates.',
                            method, resource_path
                        )
                    cache_configuration = method_meta.get('cache_configuration')
                    cache_key_parameters = cache_configuration.get(
                        'cache_key_parameters') if cache_configuration else None
                    _lambda_uri = (
                        'arn:aws:apigateway:{0}:lambda:path/'
                        '2015-03-31/functions/{1}/invocations'
                    ).format(self.connection.region, lambda_arn)
                    if existing_integration:
                        self.connection.update_integration_configuration(
                            api_id, resource_id, method,
                            int_type='AWS_PROXY' if enable_proxy else 'AWS',
                            integration_method='POST',
                            uri=_lambda_uri,
                            credentials=credentials,
                            request_templates=body_template,
                            passthrough_behavior=passthrough_behavior,
                            cache_key_parameters=cache_key_parameters,
                            request_parameters=request_parameters,
                        )
                    else:
                        self.connection.create_lambda_integration(
                            lambda_arn, api_id, resource_id, method,
                            body_template,
                            credentials=credentials,
                            passthrough_behavior=passthrough_behavior,
                            enable_proxy=enable_proxy,
                            cache_key_parameters=cache_key_parameters,
                            request_parameters=request_parameters
                        )
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
                    integration_configured = True

            elif integration_type == 'service':
                uri = method_meta.get('uri')
                role = method_meta.get('role')
                integration_method = method_meta.get('integration_method')
                _service_uri = 'arn:aws:apigateway:{0}'.format(uri)
                _service_creds = (
                    self.connection.get_service_integration_credentials(
                        self.account_id, role))
                if existing_integration:
                    self.connection.update_integration_configuration(
                        api_id, resource_id, method,
                        int_type='AWS',
                        integration_method=integration_method,
                        uri=_service_uri,
                        credentials=_service_creds,
                        request_templates=body_template,
                        passthrough_behavior=passthrough_behavior,
                        request_parameters=request_parameters,
                    )
                else:
                    self.connection.create_service_integration(
                        self.account_id,
                        api_id,
                        resource_id,
                        method,
                        integration_method,
                        role, uri,
                        body_template,
                        passthrough_behavior,
                        request_parameters)
                integration_configured = True
            elif integration_type == 'mock':
                if existing_integration:
                    self.connection.update_integration_configuration(
                        api_id, resource_id, method,
                        int_type='MOCK',
                        request_templates=body_template,
                        passthrough_behavior=passthrough_behavior,
                    )
                else:
                    self.connection.create_mock_integration(
                        api_id, resource_id,
                        method,
                        body_template,
                        passthrough_behavior)
                integration_configured = True
            elif integration_type == 'http':
                integration_method = method_meta.get('integration_method')
                uri = method_meta.get('uri')
                enable_proxy = method_meta.get('enable_proxy')
                _http_int_type = 'HTTP_PROXY' if enable_proxy else 'HTTP'
                if existing_integration:
                    self.connection.update_integration_configuration(
                        api_id, resource_id, method,
                        int_type=_http_int_type,
                        integration_method=integration_method,
                        uri=uri,
                        request_templates=body_template,
                        passthrough_behavior=passthrough_behavior,
                    )
                else:
                    self.connection.create_http_integration(
                        api_id, resource_id,
                        method,
                        integration_method,
                        uri,
                        body_template,
                        passthrough_behavior,
                        enable_proxy)
                integration_configured = True
            else:
                raise InvalidValueError(
                    f"Integration type '{integration_type}' is not supported."
                )
        if method_already_exists and integration_configured:
            self.connection.clear_method_and_integration_responses(
                api_id, resource_id, method)
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
        # fourth step: integration responses (require an integration in API GW)
        if integration_configured:
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
        return self.create_pool(self._remove_api_gateway, args)

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

    @unpack_kwargs
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
            self.connection.remove_api(api_id, log_not_found_error=False)
            group_names = self.cw_logs_conn.get_log_group_names()
            for each in group_names:
                if each.split('/')[0].endswith(api_id):
                    self.cw_logs_conn.delete_log_group_name(each)
            _LOG.info(f'API Gateway {api_id} was removed.')
            return {arn: config}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                _LOG.warning(f'API Gateway {api_id} is not found')
                return {arn: config}
            else:
                raise e

    @unpack_kwargs
    def _create_model_from_metadata(self, api_id, models):
        self._sync_models_from_meta(api_id, {'models': models})

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
        api_gw_describe = self.describe_v2_api_gateway(name, meta)
        if api_gw_describe:
            _LOG.info(f'Api gateway with name \'{name}\' exists. Returning')
            return api_gw_describe
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
                return {}
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
        return self.create_pool(self._remove_v2_api_gateway, args)

    @unpack_kwargs
    def _remove_v2_api_gateway(self, arn, config):
        api_id = config.get('description', {}).get('ApiId')
        if not api_id:
            _LOG.warning('V2 api id not found in output. Skipping')
            return {arn: config}

        lambda_arns = []
        routes = self.apigw_v2.get_routes(api_id)
        for route in routes['Items']:
            lambda_arns.append(self.apigw_v2.get_integration(
                api_id, route['Target'].replace('integrations/', '')))

        self.remove_lambdas_permissions(
            api_id, {*[arn for arn in lambda_arns if arn is not None]})
        self.apigw_v2.delete_api(api_id)
        return {arn: config}

    @staticmethod
    def extract_api_gateway_lambdas_arns(openapi_spec):
        api_gateway_lambdas_arns = {*()}

        for path, path_item in openapi_spec.get('paths', {}).items():
            for method, method_data in path_item.items():
                if not isinstance(method_data, dict):
                    continue

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

    def _is_cross_account_lambda(self, lambda_arn):
        """Check if a Lambda ARN belongs to a different AWS account"""
        try:
            # ARN format: arn:aws:lambda:region:ACCOUNT_ID:function:name
            arn_parts = lambda_arn.split(':')
            if len(arn_parts) >= 5:
                lambda_account = arn_parts[4]
                return lambda_account != self.account_id
        except (IndexError, AttributeError):
            pass
        return False
