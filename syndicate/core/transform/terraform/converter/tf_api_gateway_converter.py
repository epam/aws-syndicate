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
from syndicate.connection.api_gateway_connection import \
    REQ_VALIDATOR_PARAM_NAME, \
    REQ_VALIDATOR_PARAM_VALIDATE_BODY, REQ_VALIDATOR_PARAM_VALIDATE_PARAMS, \
    ApiGatewayConnection
from syndicate.core.resources.api_gateway_resource import API_REQUIRED_PARAMS
from syndicate.core.resources.helper import validate_params
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_api_gateway_resource_id_ref, build_api_gateway_resource_path_ref
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_function_invoke_arn_ref, build_authorizer_id_ref, \
    build_api_gateway_method_name_reference, build_function_name_ref, \
    build_rest_api_id_ref, build_api_gateway_root_resource_id_ref, \
    build_api_gateway_deployment_id_ref

NONE_AUTH = 'NONE'
CUSTOM_AUTH = 'CUSTOM'
AWS_IAM_AUTH = 'AWS_IAM'

API_GATEWAY_SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE',
                                 'OPTIONS',
                                 'HEAD', 'ANY']


class ApiGatewayConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        validate_params(name, resource, API_REQUIRED_PARAMS)

        api_name = name
        rest_api_template = generate_tf_template_for_api_gateway(
            api_name=api_name)
        self.template.add_aws_api_gateway_rest_api(meta=rest_api_template)
        auth_mappings = self._transform_authorizers(resource=resource,
                                                    api_name=api_name)

        method_names = []
        integration_names = []
        resources = resource.get('resources')
        for res_name, res in resources.items():
            api_gateway_resource, resource_name = self._create_api_gateway_resource(
                path_part=res_name, api_name=api_name)

            for http_method in API_GATEWAY_SUPPORTED_METHODS:
                method_meta = res.get(http_method)
                if method_meta:
                    tf_method_resource_name = build_terraform_resource_name(
                        resource_name, http_method)
                    method_names.append(tf_method_resource_name)
                    self.create_request_validator(method_meta=method_meta,
                                                  api_name=api_name,
                                                  resource_name=resource_name,
                                                  http_method=http_method)

                    authorizer_id = None
                    authorization_type = method_meta.get('authorization_type')
                    if authorization_type not in ['NONE', 'AWS_IAM']:
                        authorizer_id = auth_mappings.get(
                            authorization_type)
                        if not authorizer_id:
                            raise AssertionError(
                                'Authorizer {0} does not exist'.format(
                                    authorization_type))
                        authorization_type = 'CUSTOM'

                    method_request_parameters = method_meta.get(
                        'method_request_parameters')
                    method_template = get_api_gateway_method(
                        http_method=http_method,
                        resource_name=resource_name,
                        rest_api=api_name,
                        authorization=authorization_type,
                        method_name=tf_method_resource_name,
                        request_parameters=method_request_parameters,
                        authorizer_id=authorizer_id)
                    self.template.add_aws_api_gateway_method(
                        meta=method_template)

                    integration_type = method_meta.get('integration_type')
                    integration_name = build_terraform_resource_name(
                        resource_name, http_method)
                    integration_names.append(integration_name)
                    if integration_type:
                        if integration_type == 'lambda':
                            self._create_lambda_integration(
                                method_meta=method_meta,
                                method_name=tf_method_resource_name,
                                api_name=api_name,
                                integration_name=integration_name,
                                resource_name=resource_name)
                        elif integration_type == 'service':
                            self._create_service_integration(
                                resource_name=resource_name,
                                method_meta=method_meta,
                                method_name=tf_method_resource_name,
                                api_name=api_name,
                                integration_name=integration_name)
                        elif integration_type == 'mock':
                            self._create_mock_integration(
                                method_meta=method_meta,
                                resource_name=resource_name, api_name=api_name,
                                integration_name=integration_name,
                                method_name=tf_method_resource_name)
                        elif integration_type == 'http':
                            self._create_http_integration(
                                method_meta=method_meta,
                                method_name=tf_method_resource_name,
                                integration_name=integration_name,
                                resource_name=resource_name,
                                api_name=api_name)

                    responses = method_meta.get('responses')
                    for response in responses:
                        status_code = response.get('status_code')
                        method_response = api_gateway_method_response(
                            resource_name=resource_name,
                            status_code=status_code,
                            api_name=api_name,
                            http_method=http_method,
                            method_name=tf_method_resource_name)
                        self.template.add_aws_api_gateway_method_response(
                            meta=method_response)

                    integration_responses = method_meta.get(
                        'integration_responses')
                    for int_response in integration_responses:
                        status_code = int_response.get('status_code')
                        response_templates = int_response.get(
                            'response_templates')
                        error_regex = int_response.get('error_regex')
                        integration_response = create_api_gateway_integration_response(
                            resource_name=resource_name,
                            api_name=api_name,
                            status_code=status_code,
                            response_template=response_templates,
                            http_method=http_method,
                            method_name=tf_method_resource_name,
                            integration=integration_name,
                            selection_pattern=error_regex)
                        self.template.add_aws_api_gateway_integration_response(
                            meta=integration_response)

        self._create_api_gateway_deployment(resource=resource,
                                            api_name=api_name,
                                            method_names=method_names,
                                            integration_names=integration_names)

    def _create_api_gateway_deployment(self, resource, api_name, method_names,
                                       integration_names):
        deploy_stage = resource.get('deploy_stage')
        if deploy_stage:
            deployment_name = build_terraform_resource_name(api_name,
                                                            deploy_stage,
                                                            'deployment')
            deployment = api_gateway_deployment(api_name=api_name,
                                                deployment_name=deployment_name,
                                                methods=method_names,
                                                integration_names=integration_names)
            cache_cluster_configuration = resource.get(
                'cluster_cache_configuration')
            stage = api_gateway_stage(api_name=api_name,
                                      stage_name=deploy_stage,
                                      deployment_name=deployment_name,
                                      cache_cluster_configuration=cache_cluster_configuration)
            self.template.add_aws_api_gateway_stage(meta=stage)
            self.template.add_aws_api_gateway_deployment(meta=deployment)

    def _create_api_gateway_resource(self, path_part, api_name):
        resource = None
        resource_name = None
        parent_id = build_api_gateway_root_resource_id_ref(api_name=api_name)
        resource_path = path_part[1:]
        path_arr = resource_path.split('/')
        for path in path_arr:
            cur_resource_path = ''.join(path_arr[:path_arr.index(path) + 1])
            api_resource_name = build_terraform_resource_name(
                cur_resource_path, 'resource').replace('_', '-')
            existing_resource = self.template.get_resource_by_name(
                api_resource_name)
            if existing_resource:
                resource = existing_resource
                resource_name = api_resource_name
                continue
            api_gateway_resource = get_api_gateway_resource(
                path_part=path,
                rest_api=api_name,
                resource_name=api_resource_name,
                parent_id=parent_id)
            self.template.add_aws_api_gateway_resource(
                meta=api_gateway_resource)
            parent_id = build_api_gateway_resource_id_ref(
                resource_name=api_resource_name)
            resource = api_gateway_resource
            resource_name = api_resource_name
        return resource, resource_name

    def _transform_authorizers(self, resource, api_name):
        authorizer_mappings = {}
        authorizers = resource.get('authorizers', {})
        for name, val in authorizers.items():
            lambda_arn = self.define_function_arn(meta=val)

            uri = 'arn:aws:apigateway:{0}:lambda:path/2015-03-31/' \
                  'functions/{1}/invocations'.format(self.config.region,
                                                     lambda_arn)
            identity_source = val.get('identity_source')
            ttl = val.get('ttl')
            auth_type = val.get('type')

            authorizer_name = f'{api_name}_authorizer'
            authorizer_ref = build_authorizer_id_ref(
                authorizer_name=authorizer_name)
            authorizer = api_gateway_authorizer(
                authorizer_name=authorizer_name,
                authorizer_uri=uri,
                rest_api_name=api_name,
                ttl=ttl,
                identity_source=identity_source,
                auth_type=auth_type)
            self.template.add_aws_api_gateway_authorizer(meta=authorizer)
            authorizer_mappings.update({name: authorizer_ref})
        return authorizer_mappings

    def define_function_arn(self, meta):
        lambda_name = meta.get('lambda_name')

        lambda_meta = self.template.get_resource_by_name(lambda_name)
        if lambda_meta:
            return build_function_invoke_arn_ref(lambda_name)
        lambda_service = self.resources_provider.lambda_resource().lambda_conn

        function = lambda_service.get_function(lambda_name=lambda_name)
        if not function:
            raise AssertionError(
                f'Specified lambda {lambda_name} does not exists')

        version = meta.get('lambda_version')
        alias = meta.get('lambda_alias')
        if version or alias:
            return self.build_lambda_arn_with_alias(function, alias)
        else:
            return function['Configuration']['FunctionArn']

    def build_lambda_arn_with_alias(self, response, alias=None):
        name = response['Configuration']['FunctionName']
        l_arn = self.build_lambda_arn(name=name)
        version = response['Configuration']['Version']
        arn = '{0}:{1}'.format(l_arn, version)
        # override version if alias exists
        if alias:
            arn = '{0}:{1}'.format(l_arn, alias)
        return arn

    def build_lambda_arn(self, name):
        region = self.config.region
        account_id = self.config.account_id
        return f'arn:aws:lambda:{region}:{account_id}:function:{name}'

    def _create_lambda_integration(self, method_meta, method_name, api_name,
                                   integration_name, resource_name):
        enable_proxy = method_meta.get('enable_proxy')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior')
        integration_request_template = method_meta.get(
            'integration_request_body_template')

        cache_configuration = method_meta.get(
            'cache_configuration')
        cache_key_parameters = cache_configuration.get(
            'cache_key_parameters') if cache_configuration else None

        int_type = 'AWS_PROXY' if enable_proxy else 'AWS'
        uri = self.define_function_arn(meta=method_meta)

        passthrough_behavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        integration = create_api_gateway_integration(
            integration_name=integration_name,
            api_name=api_name,
            method_name=method_name,
            resource_name=resource_name,
            integration_type=int_type,
            request_template=integration_request_template,
            integration_method='POST',
            uri=uri,
            passthrough_behavior=passthrough_behavior,
            cache_key_parameters=cache_key_parameters)
        self.template.add_aws_api_gateway_integration(
            meta=integration)

    def _create_service_integration(self, method_meta, integration_name,
                                    api_name, method_name, resource_name):
        integration_request_template = method_meta.get(
            'integration_request_body_template')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior')
        uri = method_meta.get('uri')
        role = method_meta.get('role')
        integration_method = method_meta.get(
            'integration_method')
        uri = 'arn:aws:apigateway:{0}'.format(uri)

        credentials = ApiGatewayConnection.get_service_integration_credentials(
            self.config.accountId, role)
        passthrough_behavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'

        integration = create_api_gateway_integration(
            integration_name=integration_name,
            api_name=api_name,
            method_name=method_name,
            resource_name=resource_name,
            integration_type='AWS',
            request_template=integration_request_template,
            integration_method=integration_method,
            uri=uri,
            passthrough_behavior=passthrough_behavior,
            credentials=credentials)
        self.template.add_aws_api_gateway_integration(
            meta=integration)

    def _create_mock_integration(self, method_meta, integration_name, api_name,
                                 method_name, resource_name):
        integration_request_template = method_meta.get(
            'integration_request_body_template')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior')

        passthrough_behavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        integration = create_api_gateway_integration(
            integration_name=integration_name,
            api_name=api_name,
            method_name=method_name,
            resource_name=resource_name,
            integration_type='MOCK',
            request_template=integration_request_template,
            passthrough_behavior=passthrough_behavior)
        self.template.add_aws_api_gateway_integration(
            meta=integration)

    def _create_http_integration(self, method_meta, integration_name, api_name,
                                 method_name, resource_name):
        integration_request_template = method_meta.get(
            'integration_request_body_template')
        passthrough_behavior = method_meta.get(
            'integration_passthrough_behavior')

        integration_method = method_meta.get(
            'integration_method')
        uri = method_meta.get('uri')
        enable_proxy = method_meta.get('enable_proxy')

        int_type = 'HTTP_PROXY' if enable_proxy else 'HTTP'
        passthrough_behavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
        integration = create_api_gateway_integration(
            integration_name=integration_name,
            api_name=api_name,
            method_name=method_name,
            resource_name=resource_name,
            integration_type=int_type,
            request_template=integration_request_template,
            integration_method=integration_method,
            uri=uri,
            passthrough_behavior=passthrough_behavior)
        self.template.add_aws_api_gateway_integration(
            meta=integration)

    def _get_api_source_arn(self, rest_api_name, method_name, resource_name):
        rest_api_id = build_rest_api_id_ref(api_name=rest_api_name)
        region = '${' + self.config.region + '}'
        account_id = '${' + self.config.accountId + '}'
        method = build_api_gateway_method_name_reference(
            method_name=method_name)
        resource = build_api_gateway_resource_path_ref(
            resource_name=resource_name)
        return f'arn:aws:execute-api:{region}:{account_id}:{rest_api_id}/*/{method}{resource}'

    def _get_lambda_function_uri(self, lambda_name):
        region = self.config.region
        lambda_arn = build_function_invoke_arn_ref(lambda_name)
        arn = f'arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        return arn

    def create_request_validator(self, method_meta, resource_name, api_name,
                                 http_method):
        request_validator_meta = method_meta.get('request_validator')
        if request_validator_meta:
            validator_params = \
                ApiGatewayConnection.get_request_validator_params(
                    request_validator_meta)
            validator_name = validator_params.get(REQ_VALIDATOR_PARAM_NAME)
            validate_body = validator_params.get(
                REQ_VALIDATOR_PARAM_VALIDATE_BODY)
            validate_param = validator_params.get(
                REQ_VALIDATOR_PARAM_VALIDATE_PARAMS)

            tf_validator_res_name = build_terraform_resource_name(api_name,
                                                                  resource_name,
                                                                  http_method,
                                                                  'Validator')
            request_validator = aws_api_gateway_request_validator(
                resource_name=tf_validator_res_name,
                validator_name=validator_name,
                validate_request_body=validate_body,
                validate_request_parameters=validate_param,
                rest_api_name=api_name)
            self.template.add_aws_api_gateway_request_validator(
                meta=request_validator)


def aws_api_gateway_request_validator(resource_name, validator_name,
                                      rest_api_name,
                                      validate_request_body=None,
                                      validate_request_parameters=None):
    validator = {
        'name': validator_name,
        'rest_api_id': build_rest_api_id_ref(api_name=rest_api_name)
    }
    if validate_request_body:
        validator['validate_request_body'] = validate_request_body
    if validate_request_parameters:
        validator['validate_request_parameters'] = validate_request_parameters
    resource = {
        resource_name: validator
    }
    return resource


def generate_tf_template_for_api_gateway(api_name):
    resource = {
        api_name:
            {
                "endpoint_configuration": [
                    {
                        "types": [
                            "REGIONAL"
                        ]
                    }
                ],
                "name": api_name
            }
    }
    return resource


def get_api_gateway_resource(resource_name, path_part, rest_api, parent_id):
    rest_api_id = build_rest_api_id_ref(api_name=rest_api)
    resource = {
        resource_name:
            {
                "parent_id": parent_id,
                "path_part": path_part,
                "rest_api_id": rest_api_id
            }
    }
    return resource


def api_gateway_method_response(method_name, status_code, http_method,
                                resource_name, api_name):
    response_name = build_terraform_resource_name(resource_name, http_method,
                                                  status_code)
    method = build_api_gateway_method_name_reference(method_name=method_name)
    resource_id = build_api_gateway_resource_id_ref(
        resource_name=resource_name)
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    resource = {
        response_name:
            {
                "http_method": method,
                "resource_id": resource_id,
                "rest_api_id": rest_api_id,
                "status_code": status_code
            }
    }
    return resource


def create_api_gateway_integration(integration_name, api_name,
                                   resource_name,
                                   method_name, integration_type,
                                   request_template=None,
                                   integration_method=None,
                                   uri=None,
                                   passthrough_behavior=None,
                                   credentials=None,
                                   cache_key_parameters=None):
    resource_id = build_api_gateway_resource_id_ref(
        resource_name=resource_name)
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    http_method = build_api_gateway_method_name_reference(method_name)

    integration = {
        "http_method": http_method,
        "resource_id": resource_id,
        "rest_api_id": rest_api_id,
        "type": integration_type,
        "uri": uri
    }

    if request_template:
        integration.update({"request_templates": request_template})

    if integration_method:
        integration.update({'integration_http_method': integration_method})

    if passthrough_behavior:
        integration.update({'passthrough_behavior': passthrough_behavior})

    if credentials:
        integration.update({'credentials': credentials})

    if cache_key_parameters:
        integration.update({'cache_key_parameters': cache_key_parameters})

    resource = {
        integration_name: integration
    }
    return resource


def api_gateway_stage(api_name, stage_name, deployment_name,
                      cache_cluster_configuration=None):
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    deployment_id = build_api_gateway_deployment_id_ref(
        deployment_name=deployment_name)

    stage_meta = {
        "deployment_id": deployment_id,
        "rest_api_id": rest_api_id,
        "stage_name": stage_name
    }

    if cache_cluster_configuration:
        cache_cluster_enabled = cache_cluster_configuration.get(
            'cache_enabled')
        cache_size_value = cache_cluster_configuration.get(
            'cache_size')
        cache_cluster_size = str(cache_size_value)

        if str(cache_cluster_enabled).lower() == 'true':
            stage_meta['cache_cluster_enabled'] = cache_cluster_enabled
        if cache_cluster_size:
            stage_meta['cache_cluster_size'] = cache_cluster_size

    stage_resource_name = build_terraform_resource_name(api_name, 'stage')
    resource = {
        stage_resource_name: stage_meta
    }
    return resource


def api_gateway_deployment(api_name, deployment_name, methods,
                           integration_names):
    dependencies = []
    for method in methods:
        dependencies.append(f'aws_api_gateway_method.{method}')
    for integration in integration_names:
        dependencies.append(f'aws_api_gateway_integration.{integration}')

    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    resource = {
        deployment_name:
            {
                "rest_api_id": rest_api_id,
                "depends_on": dependencies
            }
    }
    return resource


def create_api_gateway_integration_response(resource_name, api_name,
                                            status_code, response_template,
                                            http_method, method_name,
                                            integration,
                                            selection_pattern=None):
    integration_response_name = build_terraform_resource_name(resource_name,
                                                              http_method,
                                                              status_code)
    method = build_api_gateway_method_name_reference(method_name)
    resource_id = build_api_gateway_resource_id_ref(
        resource_name=resource_name)
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    resource = {
        integration_response_name: [
            {
                "http_method": method,
                "resource_id": resource_id,
                "response_templates": response_template,
                "rest_api_id": rest_api_id,
                "status_code": status_code,
                "selection_pattern": selection_pattern,
                "depends_on": [
                    f'aws_api_gateway_integration.{integration}']
            }
        ]
    }
    return resource


def get_api_gateway_method(http_method, resource_name, rest_api,
                           method_name,
                           authorization=None,
                           authorizer_id=None,
                           request_parameters=None):
    resource_id = build_api_gateway_resource_id_ref(
        resource_name=resource_name)
    rest_api_id = build_rest_api_id_ref(api_name=rest_api)

    method_meta = {
        "authorization": authorization,
        "http_method": http_method,
        "resource_id": resource_id,
        "rest_api_id": rest_api_id
    }

    if authorizer_id:
        method_meta.update({'authorizer_id': authorizer_id})

    if request_parameters:
        method_meta.update({'request_parameters': request_parameters})

    resource = {
        method_name: [method_meta]
    }
    return resource


def get_api_gateway_stage(stage_name, deployment, rest_api):
    deployment_id = build_api_gateway_deployment_id_ref(
        deployment_name=deployment)
    rest_api_id = build_rest_api_id_ref(api_name=rest_api)
    resource = {
        stage_name: [
            {
                "deployment_id": deployment_id,
                "rest_api_id": rest_api_id,
                "stage_name": stage_name
            }
        ]
    }
    return resource


def aws_lambda_permissions(resource_name, function_name, api_source_arn):
    resource = {
        resource_name: [
            {
                "action": "lambda:InvokeFunction",
                "function_name": build_function_name_ref(function_name),
                "principal": "apigateway.amazonaws.com",
                "source_arn": api_source_arn,
                "statement_id": "AllowExecutionFromAPIGateway"
            }
        ]
    }
    return resource


def api_gateway_authorizer(authorizer_name,
                           authorizer_uri,
                           rest_api_name,
                           identity_source=None,
                           ttl=None,
                           auth_type=None):
    rest_api_id = build_rest_api_id_ref(api_name=rest_api_name)

    authorizer = {
        "authorizer_uri": authorizer_uri,
        "name": authorizer_name,
        "rest_api_id": rest_api_id
    }

    if identity_source:
        authorizer.update({'identity_source': identity_source})
    if ttl:
        authorizer.update({'authorizer_result_ttl_in_seconds': ttl})
    if auth_type:
        authorizer.update({'type': auth_type})

    resource = {
        authorizer_name: [authorizer]
    }
    return resource
