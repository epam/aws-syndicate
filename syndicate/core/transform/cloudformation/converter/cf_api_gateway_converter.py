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
from troposphere import apigateway, awslambda, GetAtt, Ref

from syndicate.core.resources.api_gateway_resource import ApiGatewayResource, SUPPORTED_METHODS
from ..cf_transform_helper import (to_logic_name,
                                   lambda_publish_version_logic_name,
                                   lambda_alias_logic_name,
                                   lambda_function_logic_name)
from .cf_resource_converter import CfResourceConverter


class CfApiGatewayConverter(CfResourceConverter):

    def convert(self, name, meta):
        rest_api = apigateway.RestApi(to_logic_name(name))
        rest_api.Name = name
        rest_api.BinaryMediaTypes = meta.get('binary_media_types')
        self.template.add_resource(rest_api)

        api_id = Ref(rest_api)
        authorizers = meta.get('authorizers', {})
        authorizer_resources = self._transform_authorizers(
            authorizers=authorizers,
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
                self._transform_resource(rest_api=rest_api,
                                         resource_path=path)
                for method, method_meta in resource_meta.items():
                    if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                        continue
                    resp = ApiGatewayResource.init_method_responses(
                        api_resp=api_resp,
                        method_meta=method_meta)
                    integr_resp = ApiGatewayResource.init_integration_method_responses(
                        api_integration_resp=api_integration_resp,
                        method_meta=method_meta)
                    authorizers_mapping = {x.Name: Ref(x) for x in authorizer_resources}
                    # TODO: Finish resource methods
        stage_name = \
            ApiGatewayResource.get_deploy_stage_name(meta['deploy_stage'])
        cache_cluster_configuration = meta.get('cluster_cache_configuration')
        cache_cluster_enabled = cache_cluster_configuration.get(
            'cache_enabled') if cache_cluster_configuration else None
        cache_size_value = cache_cluster_configuration.get(
            'cache_size') if cache_cluster_configuration else None
        cache_cluster_size = \
            str(cache_size_value) if cache_size_value else None
        cache_ttl_sec = cache_cluster_configuration.get('cache_ttl_sec')

        deployment = apigateway.Deployment(
            to_logic_name('{}Deployment'.format(rest_api.title)))
        stage = apigateway.StageDescription(
            CacheClusterEnabled=str(cache_cluster_enabled).lower() == 'true',
            CacheClusterSize=cache_cluster_size)
        if cache_cluster_enabled:
            stage.CacheTtlInSeconds = cache_ttl_sec
        deployment.StageDescription = stage
        deployment.RestApiId = api_id
        deployment.StageName = stage_name

    def _transform_authorizers(self, authorizers, rest_api):
        authorizer_resources = list()
        for key, val in authorizers.items():
            authorizer_name = to_logic_name('{}Authorizer'.format(key))
            authorizer = apigateway.Authorizer(authorizer_name)
            authorizer.RestApiId = Ref(rest_api)
            authorizer.Type = val.get('type')
            authorizer.AuthorizerResultTtlInSeconds = val.get('ttl')
            authorizer.IdentitySource = val.get('identity_source')

            lambda_name = val.get('lambda_name')
            lambda_version = val.get('lambda_version')
            lambda_alias = val.get('lambda_alias')
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

            authorizer_uri = ApiGatewayResource.get_authorizer_uri(
                region=self.config.region,
                lambda_arn=function_arn)
            authorizer.AuthorizerUri = authorizer_uri
            self.template.add_resource(authorizer)
            authorizer_resources.append(authorizer)

            lambda_permission = awslambda.Permission(to_logic_name(
                '{0}{1}Permission'.format(lambda_name, rest_api.title)))
            lambda_permission.FunctionName = function_arn
            lambda_permission.Action = 'lambda:InvokeFunction'
            lambda_permission.Principal = 'apigateway.amazonaws.com'
            self.template.add_resource(lambda_permission)
            return authorizer_resources

    def _transform_resource(self, rest_api, resource_path):
        parent_resource_id = GetAtt(rest_api.title, 'RootResourceId')
        resource_path = resource_path[1:]
        resource_path_split = resource_path.split('/')
        for resource in resource_path_split:
            cur_resource_path = ''.join(resource_path.partition(resource)[:2])
            resource = apigateway.Resource(to_logic_name(
                '{}ApiGatewayResource'.format(cur_resource_path)))
            resource.ParentId = parent_resource_id
            resource.PathPart = resource
            resource.RestApiId = Ref(rest_api)
            self.template.add_resource(resource)
            parent_resource_id = Ref(resource)
