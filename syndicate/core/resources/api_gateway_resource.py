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

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
from syndicate.connection.api_gateway_connection import ApiGatewayV2Connection

API_REQUIRED_PARAMS = ['resources', 'deploy_stage']

_LOG = get_logger('syndicate.core.resources.api_gateway_resource')

SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',
                     'HEAD', 'ANY']
_CORS_HEADER_NAME = 'Access-Control-Allow-Origin'
_CORS_HEADER_VALUE = "'*'"
_COGNITO_AUTHORIZER_TYPE = 'COGNITO_USER_POOLS'
_CUSTOM_AUTHORIZER_TYPE = 'CUSTOM'

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


class ApiGatewayResource(BaseResource):

    def __init__(self, apigw_conn, apigw_v2_conn: ApiGatewayV2Connection,
                 lambda_res, cognito_res, account_id, region) -> None:
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

    def api_gateway_update_processor(self, args):
        return self.create_pool(self._create_or_update_api_gateway, args, 1)

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

    def configure_cache(self, api_id, stage_name, api_resources):
        for resource_path, resource_meta in api_resources.items():
            for method_name, method_meta in resource_meta.items():
                if method_name in SUPPORTED_METHODS:
                    cache_configuration = method_meta.get(
                        'cache_configuration')
                    if not cache_configuration:
                        continue
                    cache_ttl_setting = cache_configuration.get(
                        'cache_ttl_sec')
                    encrypt_cache_data = cache_configuration.get(
                        'encrypt_cache_data')
                    if cache_ttl_setting:
                        _LOG.info(
                            'Configuring cache for {0}; TTL: {1}'.format(
                                resource_path, cache_ttl_setting))
                        escaped_resource = self._escape_path(resource_path)
                        patch_operations = [
                            {
                                'op': 'replace',
                                'path': '/{0}/{1}/caching/ttlInSeconds'.format(
                                    escaped_resource,
                                    method_name),
                                'value': str(cache_ttl_setting),
                            },
                            {
                                'op': 'replace',
                                'path': '/{0}/{1}/caching/enabled'.format(
                                    escaped_resource,
                                    method_name),
                                'value': 'True',
                            }
                        ]
                        if encrypt_cache_data is not None:
                            patch_operations.append({
                                'op': 'replace',
                                'path': '/{0}/{1}/caching/dataEncrypted'.format(
                                    escaped_resource,
                                    method_name),
                                'value': 'true' if bool(
                                    encrypt_cache_data) else 'false'
                            })
                        self.connection.update_configuration(
                            rest_api_id=api_id,
                            stage_name=stage_name,
                            patch_operations=patch_operations
                        )
                        _LOG.info(
                            'Cache for {0} was configured'.format(
                                resource_path))

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
        # api_gw_describe = self.describe_api_resources(name, meta)
        # if api_gw_describe:
        #     _LOG.info(f'Api gateway with name \'{name}\' exists. Returning')
        #     return api_gw_describe
        # _LOG.info(f'Api gateway with name \'{name}\' does not exist. Creating')
        api_item = self.connection.create_rest_api(
            api_name=name,
            binary_media_types=meta.get('binary_media_types'))
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
                self.lambda_res.add_invocation_permission(
                    statement_id=api_id,
                    name=lambda_arn,
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
        # configure caching
        if root_cache_enabled:
            _LOG.debug('Cluster cache configuration found:{0}'.format(
                cache_cluster_configuration))
            # set default ttl for root endpoint
            patch_operations = []
            cluster_cache_ttl_sec = cache_cluster_configuration.get(
                'cache_ttl_sec')
            encrypt_cache_data = cache_cluster_configuration.get(
                'encrypt_cache_data')
            if cluster_cache_ttl_sec:
                patch_operations.append({
                    'op': 'replace',
                    'path': '/*/*/caching/ttlInSeconds',
                    'value': str(cluster_cache_ttl_sec),
                })
            if encrypt_cache_data is not None:
                patch_operations.append({
                    'op': 'replace',
                    'path': '/*/*/caching/dataEncrypted',
                    'value': 'true' if bool(encrypt_cache_data) else 'false'
                })
            if patch_operations:
                self.connection.update_configuration(
                    rest_api_id=api_id,
                    stage_name=deploy_stage,
                    patch_operations=patch_operations
                )
            # customize cache settings for endpoints
            self.configure_cache(api_id, deploy_stage, api_resources)

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
        _LOG.info('Created %s API Gateway.', name)
        arn = 'arn:aws:apigateway:{0}::/restapis/{1}'.format(self.region,
                                                             api_id)
        return {
            arn: build_description_obj(response, name, meta)
        }

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
        self._remove_invocation_permissions_from_lambdas(config)
        try:
            self.connection.remove_api(api_id)
            _LOG.info(f'API Gateway {api_id} was removed.')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                _LOG.warn('API Gateway %s is not found', api_id)
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
            name=name, route_selection_expression=route_selection_expression)
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
        self.apigw_v2.delete_api(api_id)
        return
