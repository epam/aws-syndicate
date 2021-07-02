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
from troposphere import apigateway, awslambda, GetAtt, Ref, Join

from syndicate.commons.log_helper import get_logger
from syndicate.connection import ApiGatewayConnection
from syndicate.connection.api_gateway_connection import \
    (REQ_VALIDATOR_PARAM_NAME,
     REQ_VALIDATOR_PARAM_VALIDATE_BODY,
     REQ_VALIDATOR_PARAM_VALIDATE_PARAMS, RESPONSE_PARAM_ALLOW_HEADERS, RESPONSE_PARAM_ALLOW_METHODS,
     RESPONSE_PARAM_ALLOW_ORIGIN)
from syndicate.core.resources.api_gateway_resource import ApiGatewayResource, SUPPORTED_METHODS
from ..cf_transform_helper import (to_logic_name,
                                   lambda_publish_version_logic_name,
                                   lambda_alias_logic_name,
                                   lambda_function_logic_name)
from .cf_resource_converter import CfResourceConverter

_LOG = get_logger('syndicate.core.transform.cloudformation.'
                  'converter.cf_api_gateway_converter')


class CfApiGatewayConverter(CfResourceConverter):

    def convert(self, name, meta):
        rest_api = apigateway.RestApi(to_logic_name(name))
        rest_api.Name = name
        binary_media_types = meta.get('binary_media_types')
        if binary_media_types:
            rest_api.BinaryMediaTypes = binary_media_types
        self.template.add_resource(rest_api)

        api_id = Ref(rest_api)
        authorizers_meta = meta.get('authorizers', {})
        authorizers = {}
        if authorizers_meta:
            authorizers = self._transform_authorizers(
                authorizers_meta=authorizers_meta,
                rest_api=rest_api)

        api_resources = meta.get('resources')
        api_resp = meta.get('api_method_responses')
        api_integration_resp = meta.get('api_method_integration_responses')
        if api_resources:
            for path, resource_meta in api_resources.items():
                if not path.startswith('/'):
                    raise AssertionError(
                        "API resource must starts with '/', "
                        "but found {}".format(path))
                enable_cors = str(resource_meta.get('enable_cors')).lower() == 'true'
                target_resource = self._transform_resource(rest_api=rest_api,
                                                           resource_path=path)
                for method, method_meta in resource_meta.items():
                    method_res = apigateway.Method(to_logic_name('{0}{1}Method'.format(path, method)))
                    if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                        continue
                    responses_meta = ApiGatewayResource.init_method_responses(
                        api_resp=api_resp,
                        method_meta=method_meta)
                    integr_responses_meta = ApiGatewayResource.init_integration_method_responses(
                        api_integration_resp=api_integration_resp,
                        method_meta=method_meta)
                    authorizers_mapping = {x.Name: Ref(x) for x in authorizers}

                    authorization_type = method_meta.get('authorization_type')
                    authorizer_id = None
                    if authorization_type not in ['NONE', 'AWS_IAM']:
                        authorizer_id = authorizers_mapping.get(authorization_type)
                        if not authorizer_id:
                            raise AssertionError(  # TODO:Redo error messages? e.g."Authorizer is not described in meta"
                                'Authorizer {0} does not exist'.format(authorization_type))
                        authorization_type = 'CUSTOM'
                    request_validator_meta = method_meta.get('request_validator')
                    if request_validator_meta:
                        validator_params = \
                            ApiGatewayConnection.get_request_validator_params(request_validator_meta)
                        request_validator = apigateway.RequestValidator(
                            to_logic_name('{}RequestValidator'.format(method_res.title)))
                        request_validator.Name = validator_params.get(REQ_VALIDATOR_PARAM_NAME)
                        request_validator.RestApiId = Ref(rest_api)
                        request_validator.ValidateRequestBody = validator_params.get(REQ_VALIDATOR_PARAM_VALIDATE_BODY)
                        request_validator.ValidateRequestParameters = validator_params.get(
                            REQ_VALIDATOR_PARAM_VALIDATE_PARAMS)
                        self.template.add_resource(request_validator)
                        method_res.RequestValidatorId = Ref(request_validator)

                    integration_type = method_meta.get('integration_type')
                    body_template = method_meta.get('integration_request_body_template')
                    passthrough_behavior = method_meta.get(
                        'integration_passthrough_behavior')
                    request_parameters = method_meta.get('integration_request_parameters')
                    integration = None
                    if integration_type:
                        if integration_type == 'lambda':
                            lambda_name = method_meta['lambda_name']
                            lambda_version = method_meta.get('lambda_version')
                            lambda_alias = method_meta.get('lambda_alias')
                            function_arn = self._resolve_function_arn(lambda_name=lambda_name,
                                                                      lambda_alias=lambda_alias,
                                                                      lambda_version=lambda_version)
                            enable_proxy = method_meta.get('enable_proxy')
                            cache_configuration = method_meta.get('cache_configuration')
                            cache_key_parameters = cache_configuration.get(
                                'cache_key_parameters') if cache_configuration else None
                            integration = apigateway.Integration(
                                to_logic_name('{0}{1}Integration'.format(path, method)))
                            lambda_uri = self.get_lambda_function_uri(lambda_arn=function_arn)
                            if cache_key_parameters:
                                integration.CacheKeyParameters = cache_key_parameters
                            if method_meta.get('lambda_region'):
                                integration.Credentials = method_meta.get('lambda_region')
                            integration.IntegrationHttpMethod = 'POST'
                            integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
                            integration.RequestTemplates = body_template
                            integration.Type = 'AWS_PROXY' if enable_proxy else 'AWS'
                            integration.Uri = lambda_uri

                            api_source_arn = self.get_execute_api_rest_endpoint_arn(
                                api_id=api_id,
                                method=method,
                                resource_path=path)
                            self._transform_lambda_permission(function_arn=function_arn,
                                                              lambda_name=lambda_name,
                                                              rest_api=rest_api,
                                                              source_arn=api_source_arn,
                                                              endpoint=path + method)
                        elif integration_type == 'service':
                            uri = method_meta.get('uri')
                            role = method_meta.get('role')
                            integration_method = method_meta.get('integration_method')
                            credentials = ApiGatewayConnection.get_service_integration_credentials(
                                self.config.account_id, role)
                            integration = apigateway.Integration(
                                to_logic_name('{0}{1}Integration'.format(path, method)))
                            integration.Credentials = credentials
                            integration.IntegrationHttpMethod = integration_method
                            integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
                            integration.RequestParameters = request_parameters
                            integration.RequestTemplates = body_template
                            integration.Type = 'AWS'
                            integration.Uri = 'arn:aws:apigateway:{0}'.format(uri)
                        elif integration_type == 'mock':
                            integration = apigateway.Integration(
                                to_logic_name('{0}{1}Integration'.format(path, method)))
                            integration.PassthroughBehavior = passthrough_behavior
                            integration.RequestTemplates = body_template
                            integration.Type = 'MOCK'
                        elif integration_type == 'http':
                            enable_proxy = method_meta.get('enable_proxy')
                            integration_method = method_meta.get('integration_method')
                            uri = method_meta.get('uri')
                            integration = apigateway.Integration(
                                to_logic_name('{0}{1}Integration'.format(path, method)))
                            integration.IntegrationHttpMethod = integration_method
                            integration.PassthroughBehavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
                            integration.RequestTemplates = body_template
                            integration.Type = 'HTTP_PROXY' if enable_proxy else 'HTTP'
                            integration.Uri = uri
                        else:
                            raise AssertionError(
                                '{} integration type does not exist.'.format(integration_type))

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

                    responses = []
                    if responses_meta:
                        for each in responses_meta:
                            status_code = each.get('status_code')
                            resp_params = each.get('response_parameters', {})
                            resp_models = each.get('response_models')
                            responses.append(self._transform_method_response(
                                enable_cors=enable_cors,
                                status_code=status_code,
                                response_params=resp_params,
                                response_models=resp_models))
                    else:
                        responses.append(self._transform_method_response(
                            enable_cors=enable_cors))
                    method_res.MethodResponses = responses

                    integration_responses = []
                    if integration:
                        if integr_responses_meta:
                            for each in integr_responses_meta:
                                status_code = each.get('status_code')
                                response_params = each.get('response_parameters')
                                response_templates = each.get('response_templates')
                                error_regex = each.get('error_regex')
                                integration_responses.append(self._transform_integration_method_response(
                                    enable_cors=enable_cors,
                                    status_code=status_code,
                                    response_params=response_params,
                                    response_templates=response_templates,
                                    selection_pattern=error_regex))
                        else:
                            integration_responses.append(self._transform_integration_method_response(
                                enable_cors=enable_cors))
                        integration.IntegrationResponses = integration_responses
                if enable_cors:
                    method = 'OPTIONS'
                    options_method = apigateway.Method(to_logic_name('{0}{1}Method'.format(path, method)))
                    options_method.HttpMethod = method
                    options_method.AuthorizationType = 'NONE'
                    options_method.ResourceId = Ref(target_resource)
                    options_method.RestApiId = Ref(rest_api)
                    self.template.add_resource(options_method)

                    integration = apigateway.Integration(
                        to_logic_name('{0}{1}Integration'.format(path, method)))
                    integration.RequestTemplates = {
                        'application/json': '{"statusCode": 200}'
                    }
                    integration.Type = 'MOCK'
                    options_method.Integration = integration

                    method_resp = self._transform_method_response(
                        response_params={
                            RESPONSE_PARAM_ALLOW_HEADERS: False,
                            RESPONSE_PARAM_ALLOW_METHODS: False,
                            RESPONSE_PARAM_ALLOW_ORIGIN: False
                        })
                    options_method.MethodResponses = [method_resp]

                    content_types = ("'Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                                     "X-Amz-Security-Token'")
                    integr_resp = self._transform_integration_method_response(
                        response_params={
                            RESPONSE_PARAM_ALLOW_HEADERS: content_types,
                            RESPONSE_PARAM_ALLOW_METHODS: "'*'",
                            RESPONSE_PARAM_ALLOW_ORIGIN: "'*'"
                        })
                    integration.IntegrationResponses = [integr_resp]
        stage_name = \
            ApiGatewayResource.get_deploy_stage_name(meta.get('deploy_stage'))
        cache_cluster_configuration = meta.get('cluster_cache_configuration')
        cache_cluster_enabled = cache_cluster_configuration.get(
            'cache_enabled') if cache_cluster_configuration else None
        cache_size_value = cache_cluster_configuration.get(
            'cache_size') if cache_cluster_configuration else None
        cache_cluster_size = \
            str(cache_size_value) if cache_size_value else None

        deployment = apigateway.Deployment(
            to_logic_name('{}Deployment'.format(rest_api.title)))
        stage = apigateway.StageDescription()
        if str(cache_cluster_enabled).lower() == 'true':
            stage.CacheClusterEnabled = True
        if cache_cluster_size:
            stage.CacheClusterSize = cache_cluster_size
        if cache_cluster_enabled:
            cache_ttl_sec = cache_cluster_configuration.get('cache_ttl_sec')
            stage.CacheTtlInSeconds = cache_ttl_sec
        deployment.StageDescription = stage
        deployment.RestApiId = api_id
        deployment.StageName = stage_name

    def get_lambda_function_uri(self, lambda_arn):
        left_part = 'arn:aws:apigateway:{0}:lambda:path' \
                    '/2015-03-31/functions/'.format(self.config.region)
        right_part = '/invocations'
        return Join('', [left_part, lambda_arn, right_part])

    def get_execute_api_rest_endpoint_arn(self, api_id, method, resource_path,
                                          stage='*'):
        left_part = 'arn:aws:execute-api:{0}:{1}:'.format(
            self.config.region, self.config.account_id)
        right_part = '/{0}/{1}{2}'.format(stage, method, resource_path)
        return Join('', [left_part, api_id, right_part])

    @staticmethod
    def _transform_method_response(enable_cors=False, status_code=None,
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
    def _transform_integration_method_response(enable_cors=False,
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

    def _transform_authorizers(self, authorizers_meta, rest_api):
        authorizer_resources = list()
        for key, val in authorizers_meta.items():
            authorizer_name = to_logic_name('{}Authorizer'.format(key))
            authorizer = apigateway.Authorizer(authorizer_name)
            authorizer.RestApiId = Ref(rest_api)
            authorizer.Type = val.get('type')
            authorizer.AuthorizerResultTtlInSeconds = val.get('ttl')
            authorizer.IdentitySource = val.get('identity_source')

            lambda_name = val.get('lambda_name')
            lambda_version = val.get('lambda_version')
            lambda_alias = val.get('lambda_alias')
            function_arn = self._resolve_function_arn(lambda_name, lambda_alias, lambda_version)

            authorizer_uri = self.get_lambda_function_uri(lambda_arn=function_arn)
            authorizer.AuthorizerUri = authorizer_uri
            self.template.add_resource(authorizer)
            authorizer_resources.append(authorizer)

            self._transform_lambda_permission(function_arn=function_arn,
                                              lambda_name=lambda_name,
                                              rest_api=rest_api)
            return authorizer_resources

    def _transform_lambda_permission(self, function_arn, lambda_name, rest_api, source_arn=None, endpoint=''):
        lambda_permission = awslambda.Permission(to_logic_name(
            '{0}{1}{2}Permission'.format(lambda_name, rest_api.title, endpoint)))
        lambda_permission.FunctionName = function_arn
        lambda_permission.Action = 'lambda:InvokeFunction'
        lambda_permission.Principal = 'apigateway.amazonaws.com'
        if source_arn:
            lambda_permission.SourceArn = source_arn
        self.template.add_resource(lambda_permission)

    def _transform_resource(self, rest_api, resource_path):
        parent_resource_id = GetAtt(rest_api.title, 'RootResourceId')
        resource_path = resource_path[1:]
        resource_path_split = resource_path.split('/')
        target_resource = None
        for path_part in resource_path_split:
            cur_resource_path = ''.join(resource_path.partition(path_part)[:2])
            api_resource_name = to_logic_name('{}ApiGatewayResource'.format(cur_resource_path))
            existing_resource = self.get_resource(api_resource_name)
            if existing_resource:
                target_resource = existing_resource
                continue
            resource = apigateway.Resource(api_resource_name)
            resource.ParentId = parent_resource_id
            resource.PathPart = path_part
            resource.RestApiId = Ref(rest_api)
            self.template.add_resource(resource)
            target_resource = resource
            parent_resource_id = Ref(resource)
        return target_resource

    def _resolve_function_arn(self, lambda_name, lambda_alias, lambda_version):
        function_arn = None
        if lambda_alias:
            alias_resource = self.get_resource(
                lambda_alias_logic_name(function_name=lambda_name,
                                        alias=lambda_alias))
            if alias_resource:
                function_arn = Ref(alias_resource)
        elif lambda_version:
            version_resource = self.get_resource(
                lambda_publish_version_logic_name(
                    function_name=lambda_name))
            if version_resource:
                function_arn = Ref(version_resource)
        else:
            function_resource = self.get_resource(
                lambda_function_logic_name(function_name=lambda_name))
            if function_resource:
                function_arn = GetAtt(function_resource.title, 'Arn')
        if function_arn is None:
            lambda_service = self.resources_provider.lambda_resource()
            function_arn = \
                lambda_service.resolve_lambda_arn_by_version_and_alias(
                    name=lambda_name,
                    alias=lambda_alias,
                    version=lambda_version)
        return function_arn
