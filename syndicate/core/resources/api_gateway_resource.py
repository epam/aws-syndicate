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

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

_LOG = get_logger('syndicate.core.resources.api_gateway_resource')

SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']
_CORS_HEADER_NAME = 'Access-Control-Allow-Origin'
_CORS_HEADER_VALUE = "'*'"


class ApiGatewayResource(BaseResource):

    def __init__(self, apigw_conn, lambda_res, account_id, region) -> None:
        self.connection = apigw_conn
        self.lambda_res = lambda_res
        self.account_id = account_id
        self.region = region

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
                        api_integration_resp=api_integration_resp)
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
                    if cache_ttl_setting:
                        _LOG.info(
                            'Configuring cache for {0}; TTL: {1}'.format(
                                resource_path, cache_ttl_setting))
                        escaped_resource = self._escape_path(resource_path)
                        self.connection.update_configuration(
                            rest_api_id=api_id,
                            stage_name=stage_name,
                            patch_operations=[
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
        required_parameters = ['resources', 'deploy_stage']
        validate_params(name, meta, required_parameters)

        api_resources = meta['resources']

        api_item = self.connection.create_rest_api(name)
        api_id = api_item['id']

        # deploy authorizers
        authorizers = meta.get('authorizers', {})
        for key, val in authorizers.items():
            lambda_version = val.get('lambda_version')
            lambda_name = val.get('lambda_name')
            lambda_alias = val.get('lambda_alias')
            lambda_arn = self.lambda_res. \
                resolve_lambda_arn_by_version_and_alias(lambda_name,
                                                        lambda_version,
                                                        lambda_alias)
            uri = 'arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions/{1}/invocations'.format(
                self.region, lambda_arn)
            self.connection.create_authorizer(api_id=api_id, name=key,
                                              type=val['type'],
                                              authorizer_uri=uri,
                                              identity_source=val.get(
                                                  'identity_source'),
                                              ttl=val.get('ttl'))

            self.lambda_res.add_invocation_permission(
                statement_id=api_id,
                name=lambda_arn,
                principal='apigateway.amazonaws.com')
        if api_resources:
            api_resp = meta.get('api_method_responses')
            api_integration_resp = meta.get('api_method_integration_responses')
            args = self.__prepare_api_resources_args(api_id, api_resources,
                                                     api_resp,
                                                     api_integration_resp)
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

    def __deploy_api_gateway(self, api_id, meta, api_resources):
        deploy_stage = meta['deploy_stage']
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
            cluster_cache_ttl_sec = cache_cluster_configuration.get(
                'cache_ttl_sec')
            self.connection.update_configuration(
                rest_api_id=api_id,
                stage_name=deploy_stage,
                patch_operations=[
                    {
                        'op': 'replace',
                        'path': '/*/*/caching/ttlInSeconds',
                        'value': str(cluster_cache_ttl_sec),
                    }
                ]
            )
            # customize cache settings for endpoints
            self.configure_cache(api_id, deploy_stage, api_resources)

    def __prepare_api_resources_args(self, api_id, api_resources,
                                     api_resp=None,
                                     api_integration_resp=None):
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
                        api_integration_resp=api_integration_resp)
                else:
                    args.append({
                        'api_id': api_id,
                        'resource_path': each,
                        'resource_meta': resource_meta,
                        'authorizers_mapping': authorizers_mapping
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
                                api_integration_resp=None):
        """ Check if all specified methods exist and create some if not.
    
        :type api_id: str
        :type resource_id: str
        :type resource_meta: dict
        :type enable_cors: bool or None
        :type:
        """
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
                    enable_cors=enable_cors)
            if enable_cors and not self.connection.get_method(api_id,
                                                              resource_id,
                                                              'OPTIONS'):
                _LOG.info('Enabling CORS for resource %s...', resource_id)
                self.connection.enable_cors_for_resource(api_id, resource_id)

    @unpack_kwargs
    def _create_resource_from_metadata(self, api_id, resource_path,
                                       resource_meta,
                                       authorizers_mapping):
        self.connection.create_resource(api_id, resource_path)
        _LOG.info('Resource %s created.', resource_path)
        resource_id = self.connection.get_resource_id(api_id, resource_path)
        enable_cors = resource_meta.get('enable_cors')
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
                    authorizers_mapping=authorizers_mapping)
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

    def _create_method_from_metadata(self, api_id, resource_id, resource_path,
                                     method,
                                     method_meta, authorizers_mapping,
                                     enable_cors=False, api_resp=None,
                                     api_integration_resp=None):
        # init responses for method
        method_responses = method_meta.get("responses")
        if method_responses:
            resp = method_responses
        elif api_resp:
            resp = api_resp
        else:
            resp = []

        # init integration responses for method
        integration_method_responses = method_meta.get("integration_responses")
        if integration_method_responses:
            integr_resp = integration_method_responses
        elif api_resp:
            integr_resp = api_integration_resp
        else:
            integr_resp = []

        # resolve authorizer if needed
        authorization_type = method_meta.get('authorization_type')
        if authorization_type not in ['NONE', 'AWS_IAM']:
            # type is authorizer, so add id to meta
            authorizer_id = authorizers_mapping.get(authorization_type)
            if not authorizer_id:
                raise AssertionError(
                    'Authorizer {0} does not exist'.format(authorization_type))
            method_meta['authorizer_id'] = authorizer_id
            authorization_type = 'CUSTOM'

        self.connection.create_method(
            api_id, resource_id, method,
            authorization_type=authorization_type,
            authorizer_id=method_meta.get('authorizer_id'),
            api_key_required=method_meta.get('api_key_required'),
            request_parameters=method_meta.get('method_request_parameters'),
            request_models=method_meta.get('method_request_models'),
            request_validator=method_meta.get('request_validator'))
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
                    cache_key_parameters=cache_key_parameters)
                # add permissions to invoke
                api_source_arn = f"arn:aws:execute-api:{self.region}:" \
                    f"{self.account_id}:{api_id}/*/{method}{resource_path}"
                self.lambda_res.add_invocation_permission(
                    statement_id=(api_id + '-' + method + '-' +
                                  resource_path[1:].replace('/', '_').
                                  replace('{', '').
                                  replace('}', '')),
                    name=lambda_arn,
                    principal='apigateway.amazonaws.com',
                    source_arn=api_source_arn)
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

    def _check_existing_methods(self, api_id, resource_id, resource_path,
                                resource_meta,
                                enable_cors, authorizers_mapping,
                                api_resp=None,
                                api_integration_resp=None):
        """ Check if all specified methods exist and create some if not.
    
        :type api_id: str
        :type resource_id: str
        :type resource_meta: dict
        :type enable_cors: bool or None
        :type:
        """
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
                    enable_cors=enable_cors)
            if enable_cors and not self.connection.get_method(api_id,
                                                              resource_id,
                                                              'OPTIONS'):
                _LOG.info('Enabling CORS for resource %s...', resource_id)
                self.connection.enable_cors_for_resource(api_id, resource_id)

        @unpack_kwargs
        def _create_resource_from_metadata(self, api_id, resource_path,
                                           resource_meta,
                                           authorizers_mapping):
            self.connection.create_resource(api_id, resource_path)
            _LOG.info('Resource %s created.', resource_path)
            resource_id = self.connection.get_resource_id(api_id,
                                                          resource_path)
            enable_cors = resource_meta.get('enable_cors')
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
                        authorizers_mapping=authorizers_mapping)
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

    def _customize_gateway_responses(self, api_id):
        responses = self.connection.get_gateway_responses(api_id)
        response_types = [r['responseType'] for r in responses]
        for response_type in response_types:
            time.sleep(10)
            self.connection.add_header_to_gateway_response(api_id,
                                                           response_type,
                                                           _CORS_HEADER_NAME,
                                                           _CORS_HEADER_VALUE)

    def remove_api_gateways(self, args):
        for arg in args:
            self._remove_api_gateway(**arg)
            # wait for success deletion
            time.sleep(60)

    def _remove_api_gateway(self, arn, config):
        api_id = config['description']['id']
        try:
            self.connection.remove_api(api_id)
            _LOG.info('API Gateway %s was removed.', api_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                _LOG.warn('API Gateway %s is not found', api_id)
            else:
                raise e
