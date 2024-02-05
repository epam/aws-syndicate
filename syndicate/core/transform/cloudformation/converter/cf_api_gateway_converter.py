"""
    Copyright 2021 EPAM Systems, Inc.

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

from troposphere import apigateway, GetAtt, Ref, Join

from syndicate.commons.log_helper import get_logger
from syndicate.connection import ApiGatewayConnection
from syndicate.connection.api_gateway_connection import \
    (REQ_VALIDATOR_PARAM_NAME,
     REQ_VALIDATOR_PARAM_VALIDATE_BODY,
     REQ_VALIDATOR_PARAM_VALIDATE_PARAMS,
     RESPONSE_PARAM_ALLOW_HEADERS,
     RESPONSE_PARAM_ALLOW_METHODS,
     RESPONSE_PARAM_ALLOW_ORIGIN)
from syndicate.core.constants import API_GW_DEFAULT_THROTTLING_RATE_LIMIT, \
    API_GW_DEFAULT_THROTTLING_BURST_LIMIT
from syndicate.core.resources.api_gateway_resource import (ApiGatewayResource,
                                                           SUPPORTED_METHODS,
                                                           API_REQUIRED_PARAMS)
from syndicate.core.resources.helper import validate_params
from .cf_lambda_function_converter import CfLambdaFunctionConverter
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import (to_logic_name,
                                  lambda_publish_version_logic_name,
                                  lambda_alias_logic_name,
                                  lambda_function_logic_name,
                                  api_gateway_method_logic_name)

_LOG = get_logger('cf_api_gateway_converter')


class CfApiGatewayConverter(CfResourceConverter):

    def convert(self, name, meta):
        validate_params(name, meta, API_REQUIRED_PARAMS)
        rest_api = self._convert_rest_api(name=name, meta=meta)
        authorizers_mapping = self._convert_authorizers(meta=meta,
                                                        rest_api=rest_api)
        methods = self._convert_api_resources(
            meta=meta, rest_api=rest_api,
            authorizers_mapping=authorizers_mapping)
        self._convert_deployment(meta=meta, rest_api=rest_api, methods=methods)

    def _convert_api_resources(self, meta, rest_api, authorizers_mapping):
        api_resources = meta.get('resources')
        methods = []
        if api_resources:
            for path, resource_meta in api_resources.items():
                methods.extend(self._process_resource(authorizers_mapping, meta, path, resource_meta, rest_api))
        return methods

    def _process_resource(self, authorizers_mapping, meta, path, resource_meta, rest_api):
        if not path.startswith('/'):
            raise AssertionError(
                "API resource must starts with '/', "
                "but found {}".format(path))
        enable_cors = str(resource_meta.get('enable_cors')).lower() == 'true'
        target_resource = self._convert_resource(rest_api=rest_api,
                                                 resource_path=path)
        methods = []
        for method, method_meta in resource_meta.items():
            method_res = apigateway.Method(api_gateway_method_logic_name(path, method))
            if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                continue
            authorization_type = method_meta.get('authorization_type')
            authorizer_id = None
            if authorization_type not in ['NONE', 'AWS_IAM']:
                authorizer_id = authorizers_mapping.get(
                    to_logic_name('ApiGatewayAuthorizer', authorization_type))
                if not authorizer_id:
                    raise AssertionError(
                        'Authorizer {0} is not present in '
                        'the build meta.'.format(authorization_type))
                authorization_type = 'CUSTOM'
            self._convert_request_validator(method_meta, method_res, rest_api)

            integration_type = method_meta.get('integration_type')
            integration = self._convert_method_integration(
                integration_type=integration_type,
                method=method,
                method_meta=method_meta,
                path=path,
                rest_api=rest_api)

            method_res.ApiKeyRequired = bool(method_meta.get('api_key_required'))
            method_res.AuthorizationType = authorization_type
            if authorizer_id:
                method_res.AuthorizerId = authorizer_id
            method_res.HttpMethod = method
            if integration:
                method_res.Integration = integration
            if method_meta.get('method_request_models'):
                method_res.RequestModels = method_meta.get('method_request_models')
            if method_meta.get('method_request_parameters'):
                method_res.RequestParameters = method_meta.get('method_request_parameters')
            method_res.ResourceId = Ref(target_resource)
            method_res.RestApiId = Ref(rest_api)
            self.template.add_resource(method_res)

            responses = self._convert_method_responses(enable_cors, meta, method_meta)
            method_res.MethodResponses = responses

            integration_responses = self._convert_integration_responses(enable_cors, meta, method_meta)
            integration.IntegrationResponses = integration_responses
            methods.append(method_res)
        if enable_cors:
            methods.append(self._enable_cors_for_resource(rest_api, path, target_resource))
        return methods

    def _convert_request_validator(self, method_meta, method_resource, rest_api):
        request_validator_meta = method_meta.get('request_validator')
        if request_validator_meta:
            validator_params = \
                ApiGatewayConnection.get_request_validator_params(request_validator_meta)
            request_validator = apigateway.RequestValidator(
                to_logic_name('ApiGatewayRequestValidator', method_resource.title))
            request_validator.Name = validator_params.get(REQ_VALIDATOR_PARAM_NAME)
            request_validator.RestApiId = Ref(rest_api)
            request_validator.ValidateRequestBody = validator_params.get(REQ_VALIDATOR_PARAM_VALIDATE_BODY)
            request_validator.ValidateRequestParameters = validator_params.get(
                REQ_VALIDATOR_PARAM_VALIDATE_PARAMS)
            self.template.add_resource(request_validator)
            method_resource.RequestValidatorId = Ref(request_validator)

    def _convert_rest_api(self, name, meta):
        rest_api = apigateway.RestApi(to_logic_name('ApiGatewayRestApi', name))
        rest_api.Name = name
        binary_media_types = meta.get('binary_media_types')
        if binary_media_types:
            rest_api.BinaryMediaTypes = binary_media_types
        self.template.add_resource(rest_api)
        return rest_api

    def _convert_method_integration(self, integration_type, method, method_meta, path, rest_api):
        integration_builders = {
            'lambda': self._lambda_method_integration,
            'service': self._service_method_integration,
            'mock': self._mock_method_integration,
            'http': self._http_method_integration
        }
        if integration_type not in integration_builders:
            raise AssertionError(
                '{} integration type does not exist.'.format(integration_type))

        integration_builder = integration_builders[integration_type]
        return integration_builder(method, method_meta, path, rest_api)

    def _lambda_method_integration(self, method, method_meta, path, rest_api):
        lambda_name = method_meta.get('lambda_name')
        lambda_arn = self._resolve_lambda_arn(meta=method_meta)
        passthrough_behavior = method_meta.get('integration_passthrough_behavior')
        body_template = method_meta.get('integration_request_body_template')
        enable_proxy = method_meta.get('enable_proxy')
        cache_configuration = method_meta.get('cache_configuration')
        cache_key_parameters = cache_configuration.get(
            'cache_key_parameters') if cache_configuration else None
        integration = apigateway.Integration()
        lambda_uri = self.get_lambda_function_uri(lambda_name=lambda_name)
        if cache_key_parameters:
            integration.CacheKeyParameters = cache_key_parameters
        if method_meta.get('lambda_region'):
            integration.Credentials = method_meta.get('lambda_region')
        integration.IntegrationHttpMethod = 'POST'
        integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        if body_template:
            integration.RequestTemplates = body_template
        integration.Type = 'AWS_PROXY' if enable_proxy else 'AWS'
        integration.Uri = lambda_uri
        api_source_arn = self.get_execute_api_rest_endpoint_arn(
            api_id=Ref(rest_api),
            method=method,
            resource_path=path)
        permission = CfLambdaFunctionConverter.convert_lambda_permission(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            principal='apigateway',
            source_arn=api_source_arn,
            permission_qualifier=rest_api.Name + path + method
        )
        self.template.add_resource(permission)
        return integration

    def _service_method_integration(self, method, method_meta, path, rest_api):
        uri = method_meta.get('uri')
        role = method_meta.get('role')
        passthrough_behavior = method_meta.get('integration_passthrough_behavior')
        body_template = method_meta.get('integration_request_body_template')
        request_parameters = method_meta.get('integration_request_parameters')
        integration_method = method_meta.get('integration_method')
        if not integration_method:
            raise ValueError('integration_method is not provided for the '
                             f'{method} {path} method of the integration type "service"')
        credentials = ApiGatewayConnection.get_service_integration_credentials(
            self.config.account_id, role)
        integration = apigateway.Integration()
        integration.Credentials = credentials
        integration.IntegrationHttpMethod = integration_method
        integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        integration.RequestParameters = request_parameters
        integration.RequestTemplates = body_template
        integration.Type = 'AWS'
        integration.Uri = 'arn:aws:apigateway:{0}'.format(uri)
        return integration

    def _mock_method_integration(self, method, method_meta, path, rest_api):
        integration = apigateway.Integration()
        passthrough_behavior = method_meta.get('integration_passthrough_behavior')
        body_template = method_meta.get('integration_request_body_template')
        integration.PassthroughBehavior = passthrough_behavior
        integration.RequestTemplates = body_template
        integration.Type = 'MOCK'
        return integration

    def _http_method_integration(self, method, method_meta, path, rest_api):
        enable_proxy = method_meta.get('enable_proxy')
        integration_method = method_meta.get('integration_method')
        passthrough_behavior = method_meta.get('integration_passthrough_behavior')
        body_template = method_meta.get('integration_request_body_template')
        uri = method_meta.get('uri')
        integration = apigateway.Integration()
        integration.IntegrationHttpMethod = integration_method
        integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        integration.RequestTemplates = body_template
        integration.Type = 'HTTP_PROXY' if enable_proxy else 'HTTP'
        integration.Uri = uri
        return integration

    def _convert_method_responses(self, enable_cors, api_meta, method_meta):
        api_resp = api_meta.get('api_method_responses')
        responses_meta = ApiGatewayResource.init_method_responses(
            api_resp=api_resp,
            method_meta=method_meta)
        responses = []
        if responses_meta:
            for each in responses_meta:
                status_code = each.get('status_code')
                resp_params = each.get('response_parameters', {})
                resp_models = each.get('response_models')
                responses.append(self._convert_method_response(
                    enable_cors=enable_cors,
                    status_code=status_code,
                    response_params=resp_params,
                    response_models=resp_models))
        else:
            responses.append(self._convert_method_response(
                enable_cors=enable_cors))
        return responses

    def _convert_integration_responses(self, enable_cors, api_meta, method_meta):
        api_integration_resp = api_meta.get('api_method_integration_responses')
        integr_responses_meta = ApiGatewayResource.init_integration_method_responses(
            api_integration_resp=api_integration_resp,
            method_meta=method_meta)
        integration_responses = []
        if integr_responses_meta:
            for each in integr_responses_meta:
                status_code = each.get('status_code')
                response_params = each.get('response_parameters')
                response_templates = each.get('response_templates')
                error_regex = each.get('error_regex')
                integration_responses.append(self._convert_integration_method_response(
                    enable_cors=enable_cors,
                    status_code=status_code,
                    response_params=response_params,
                    response_templates=response_templates,
                    selection_pattern=error_regex))
        else:
            integration_responses.append(self._convert_integration_method_response(
                enable_cors=enable_cors))
        return integration_responses

    def _enable_cors_for_resource(self, rest_api, path, target_resource):
        method = 'OPTIONS'
        options_method = apigateway.Method(api_gateway_method_logic_name(path, method))
        options_method.HttpMethod = method
        options_method.AuthorizationType = 'NONE'
        options_method.ResourceId = Ref(target_resource)
        options_method.RestApiId = Ref(rest_api)
        self.template.add_resource(options_method)
        integration = apigateway.Integration()
        integration.RequestTemplates = {
            'application/json': '{"statusCode": 200}'
        }
        integration.Type = 'MOCK'
        options_method.Integration = integration
        method_resp = self._convert_method_response(
            response_params={
                RESPONSE_PARAM_ALLOW_HEADERS: False,
                RESPONSE_PARAM_ALLOW_METHODS: False,
                RESPONSE_PARAM_ALLOW_ORIGIN: False
            })
        options_method.MethodResponses = [method_resp]
        content_types = ("'Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                         "X-Amz-Security-Token'")
        integr_resp = self._convert_integration_method_response(
            response_params={
                RESPONSE_PARAM_ALLOW_HEADERS: content_types,
                RESPONSE_PARAM_ALLOW_METHODS: "'*'",
                RESPONSE_PARAM_ALLOW_ORIGIN: "'*'"
            })
        integration.IntegrationResponses = [integr_resp]
        return options_method

    def get_lambda_function_uri(self, lambda_name):
        left_part = 'arn:aws:apigateway:{0}:lambda:path' \
                    '/2015-03-31/functions/arn:aws:lambda:{0}:{1}:' \
                    'function:{2}:{3}'.format(
            self.config.region, self.config.account_id, lambda_name,
            self.config.lambdas_alias_name)
        right_part = '/invocations'
        return Join('', [left_part, right_part])

    def get_execute_api_rest_endpoint_arn(self, api_id, method, resource_path,
                                          stage='*'):
        left_part = 'arn:aws:execute-api:{0}:{1}:'.format(
            self.config.region, self.config.account_id)
        right_part = '/{0}/{1}{2}'.format(stage, method, resource_path)
        return Join('', [left_part, api_id, right_part])

    @staticmethod
    def _convert_method_response(enable_cors=False, status_code=None,
                                 response_params=None, response_models=None):
        response_allow_origin = "response.header.Access-Control-Allow-Origin"
        method_allow_origin = "method.{0}".format(response_allow_origin)
        if not response_params:
            response_params = {}
        if enable_cors:
            response_params[method_allow_origin] = False
        if not response_models:
            response_models = {'application/json': 'Empty'}
        return apigateway.MethodResponse(
            ResponseModels=response_models,
            ResponseParameters=response_params,
            StatusCode=status_code if status_code else '200')

    @staticmethod
    def _convert_integration_method_response(enable_cors=False,
                                             status_code=None,
                                             response_params=None,
                                             response_templates=None,
                                             selection_pattern=None):
        response_allow_origin = "response.header.Access-Control-Allow-Origin"
        method_allow_origin = "method.{0}".format(response_allow_origin)
        if not response_params:
            response_params = {}
        if enable_cors:
            response_params[method_allow_origin] = "'*'"
        if not response_templates:
            response_templates = {'application/json': ''}
        response = apigateway.IntegrationResponse(
            ResponseParameters=response_params,
            ResponseTemplates=response_templates,
            StatusCode=status_code if status_code else '200')
        if selection_pattern:
            response.SelectionPattern = selection_pattern
        return response

    def _convert_authorizers(self, meta, rest_api):
        authorizers_mapping = {}
        authorizers_meta = meta.get('authorizers', {})
        if authorizers_meta:
            authorizers = list()
            for key, val in authorizers_meta.items():
                authorizer_name = to_logic_name('ApiGatewayAuthorizer', key)
                authorizer = apigateway.Authorizer(authorizer_name)
                authorizer.Name = authorizer_name
                authorizer.RestApiId = Ref(rest_api)
                authorizer.Type = val.get('type')
                authorizer.AuthorizerResultTtlInSeconds = val.get('ttl')
                authorizer.IdentitySource = val.get('identity_source')

                lambda_arn = self._resolve_lambda_arn(meta=val)
                lambda_name = val.get('lambda_name')

                authorizer_uri = self.get_lambda_function_uri(lambda_name=lambda_name)
                authorizer.AuthorizerUri = authorizer_uri
                self.template.add_resource(authorizer)
                authorizers.append(authorizer)

                permission = CfLambdaFunctionConverter.convert_lambda_permission(
                    lambda_arn=lambda_arn,
                    lambda_name=lambda_name,
                    principal='apigateway'
                )
                self.template.add_resource(permission)
            authorizers_mapping = {x.Name: Ref(x) for x in authorizers}
        return authorizers_mapping

    def _convert_deployment(self, meta, rest_api, methods):
        stage_name = \
            ApiGatewayResource.get_deploy_stage_name(meta.get('deploy_stage'))
        cache_cluster_configuration = meta.get('cluster_cache_configuration')
        cache_cluster_enabled = cache_cluster_configuration.get(
            'cache_enabled') if cache_cluster_configuration else None
        cache_size_value = cache_cluster_configuration.get(
            'cache_size') if cache_cluster_configuration else None
        cache_cluster_size = \
            str(cache_size_value) if cache_size_value else None
        throttling_cluster_configuration = meta.get(
            'cluster_throttling_configuration')
        throttling_cluster_enabled = throttling_cluster_configuration.get(
            'throttling_enabled') if throttling_cluster_configuration else None
        deployment = apigateway.Deployment(
            to_logic_name('ApiGatewayDeployment', rest_api.title))
        stage = apigateway.StageDescription()
        if str(cache_cluster_enabled).lower() == 'true':
            stage.CacheClusterEnabled = True
        if cache_cluster_size:
            stage.CacheClusterSize = cache_cluster_size
        if cache_cluster_enabled:
            cache_ttl_sec = cache_cluster_configuration.get('cache_ttl_sec')
            if cache_ttl_sec is not None:
                stage.CacheTtlInSeconds = cache_ttl_sec
        if throttling_cluster_enabled:
            stage.ThrottlingRateLimit = throttling_cluster_configuration.get(
                'throttling_rate_limit', API_GW_DEFAULT_THROTTLING_RATE_LIMIT)
            stage.ThrottlingBurstLimit = throttling_cluster_configuration.get(
                'throttling_burst_limit', API_GW_DEFAULT_THROTTLING_BURST_LIMIT)
        deployment.StageDescription = stage
        deployment.RestApiId = Ref(rest_api)
        deployment.StageName = stage_name
        deployment.DependsOn = methods
        self.template.add_resource(deployment)

    def _convert_resource(self, rest_api, resource_path):
        parent_resource_id = GetAtt(rest_api.title, 'RootResourceId')
        resource_path = resource_path[1:]
        resource_path_split = resource_path.split('/')
        target_resource = None
        for path_part in resource_path_split:
            api_resource_name = to_logic_name(
                'ApiGatewayResource',
                ''.join(resource_path.partition(path_part)[:2]))
            existing_resource = self.get_resource(api_resource_name)
            if existing_resource:
                target_resource = existing_resource
                parent_resource_id = Ref(existing_resource)
                continue
            resource = apigateway.Resource(api_resource_name)
            resource.ParentId = parent_resource_id
            resource.PathPart = path_part
            resource.RestApiId = Ref(rest_api)
            self.template.add_resource(resource)
            target_resource = resource
            parent_resource_id = Ref(resource)
        return target_resource

    def _resolve_lambda_arn(self, meta):
        lambda_name = meta.get('lambda_name')
        lambda_version = meta.get('lambda_version')
        lambda_alias = meta.get('lambda_alias')
        lambda_arn = None
        if lambda_alias:
            alias_resource = self.get_resource(
                lambda_alias_logic_name(function_name=lambda_name,
                                        alias=lambda_alias))
            if alias_resource:
                lambda_arn = Ref(alias_resource)
        elif lambda_version:
            version_resource = self.get_resource(
                lambda_publish_version_logic_name(
                    function_name=lambda_name))
            if version_resource:
                lambda_arn = Ref(version_resource)
        else:
            function_resource = self.get_resource(
                lambda_function_logic_name(function_name=lambda_name))
            if function_resource:
                lambda_arn = GetAtt(function_resource.title, 'Arn')
        if lambda_arn is None:
            function_ref = lambda_name
            if lambda_alias:
                function_ref += ':' + lambda_alias
            elif lambda_version:
                function_ref += ':' + lambda_version
            raise AssertionError("Lambda function '{}' is not present "
                                 "in build meta.".format(function_ref))
            # Or lookup existing lambda function in AWS?
            # lambda_service = self.resources_provider.lambda_resource()
            # function_arn = \
            #     lambda_service.resolve_lambda_arn_by_version_and_alias(
            #         name=lambda_name,
            #         alias=lambda_alias,
            #         version=lambda_version)
        return lambda_arn
