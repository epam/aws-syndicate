from syndicate.connection import ApiGatewayConnection
from syndicate.core.resources.api_gateway_resource import SUPPORTED_METHODS
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_function_invoke_arn_ref, build_authorizer_id_ref, \
    build_method_name_reference, build_function_name_ref, \
    build_rest_api_id_ref, build_api_gateway_root_resource_id_ref, \
    build_api_gateway_deployment_id_ref, \
    build_resource_id_ref

NONE_AUTH = 'NONE'
CUSTOM_AUTH = 'CUSTOM'
AWS_IAM_AUTH = 'AWS_IAM'
COGNITO_USER_POOLS_AUTH = 'COGNITO_USER_POOLS'


class ApiGatewayConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        api_name = resource.get('resource_name')
        rest_api_template = generate_tf_template_for_api_gateway(
            api_name=api_name)
        self.template.add_aws_api_gateway_rest_api(meta=rest_api_template)
        auth_mappings = self._transform_authorizers(resource=resource,
                                                    api_name=api_name)

        method_names = []
        integration_names = []
        resources = resource.get('resources')
        for res_name, res in resources.items():
            api_gateway_resource = get_api_gateway_resource(path_part=res_name,
                                                            rest_api=api_name)
            self.template.add_aws_api_gateway_resource(
                meta=api_gateway_resource)

            for http_method in SUPPORTED_METHODS:
                method_meta = res.get(http_method)
                if method_meta:
                    resource_name = res_name.replace('/', '')

                    method_name = f'{resource_name}-{http_method}'
                    method_names.append(method_name)

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
                        method_name=method_name,
                        request_parameters=method_request_parameters,
                        authorizer_id=authorizer_id)
                    self.template.add_aws_api_gateway_method(
                        meta=method_template)

                    integration_request_template = method_meta.get(
                        'integration_request_body_template')

                    enable_proxy = method_meta.get('enable_proxy')
                    integration_type = method_meta.get('integration_type')

                    passthrough_behavior = method_meta.get(
                        'integration_passthrough_behavior')

                    integration_name = f'{resource_name}_{http_method}_integration'
                    integration_names.append(integration_name)
                    if integration_type:
                        if integration_type == 'lambda':
                            lambda_name = method_meta['lambda_name']

                            cache_configuration = method_meta.get(
                                'cache_configuration')
                            cache_key_parameters = cache_configuration.get(
                                'cache_key_parameters') if cache_configuration else None

                            int_type = 'AWS_PROXY' if enable_proxy else 'AWS'
                            lambda_arn = build_function_invoke_arn_ref(
                                lambda_name)
                            passthrough_behavior = passthrough_behavior if passthrough_behavior else 'WHEN_NO_MATCH'
                            integration = create_api_gateway_integration(
                                integration_name=integration_name,
                                api_name=api_name,
                                method_name=method_name,
                                resource_name=resource_name,
                                integration_type=int_type,
                                request_template=integration_request_template,
                                integration_method='POST',
                                uri=lambda_arn,
                                passthrough_behavior=passthrough_behavior,
                                cache_key_parameters=cache_key_parameters)
                            self.template.add_aws_api_gateway_integration(
                                meta=integration)
                        elif integration_type == 'service':
                            uri = method_meta.get('uri')
                            role = method_meta.get('role')
                            integration_method = http_method.get(
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
                        elif integration_type == 'mock':
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
                        elif integration_type == 'http':
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

                    responses = method_meta.get('responses')
                    for response in responses:
                        status_code = response.get('status_code')
                        method_response = api_gateway_method_response(
                            resource_name=resource_name,
                            status_code=status_code,
                            api_name=api_name,
                            http_method=http_method,
                            method_name=method_name)
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
                            method_name=method_name,
                            integration=integration_name,
                            selection_pattern=error_regex)
                        self.template.add_aws_api_gateway_integration_response(
                            meta=integration_response)

        deploy_stage = resource.get('deploy_stage')
        if deploy_stage:
            deployment_name = f'{deploy_stage}_deployment'
            deployment = api_gateway_deployment(api_name=api_name,
                                                deployment_name=deployment_name,
                                                methods=method_names,
                                                integration_names=integration_names)
            stage = api_gateway_stage(api_name=api_name,
                                      stage_name=deploy_stage,
                                      deployment_name=deployment_name)
            self.template.add_aws_api_gateway_stage(meta=stage)
            self.template.add_aws_api_gateway_deployment(meta=deployment)

    def _transform_authorizers(self, resource, api_name):
        authorizer_mappings = {}
        authorizers = resource.get('authorizers', {})
        for name, val in authorizers.items():
            lambda_name = val.get('lambda_name')
            lambda_arn = build_function_invoke_arn_ref(lambda_name)
            identity_source = val.get('identity_source')
            ttl = val.get('ttl')
            auth_type = val.get('type')

            authorizer_ref = build_authorizer_id_ref(authorizer_name=name)
            authorizer = api_gateway_authorizer(authorizer_name=name,
                                                authorizer_uri=lambda_arn,
                                                rest_api_name=api_name,
                                                ttl=ttl,
                                                identity_source=identity_source,
                                                auth_type=auth_type)
            self.template.add_aws_api_gateway_authorizer(meta=authorizer)
            authorizer_mappings.update({name: authorizer_ref})
        return authorizer_mappings

    def _get_api_source_arn(self, rest_api_name, method_name, resource_name):
        rest_api_id = '${aws_api_gateway_rest_api.' + rest_api_name + '.id}'
        region = '${' + self.config.region + '}'
        account_id = '${' + self.config.accountId + '}'
        method = '${aws_api_gateway_method.' + method_name + '.http_method}'
        resource = '${aws_api_gateway_resource.' + resource_name + '.path}'
        return f'arn:aws:execute-api:{region}:{account_id}:{rest_api_id}/*/{method}{resource}'

    def _get_lambda_function_uri(self, lambda_name):
        region = self.config.region
        lambda_arn = build_function_invoke_arn_ref(lambda_name)
        arn = f'arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        return arn


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


def get_api_gateway_resource(path_part, rest_api):
    resource_name = path_part.replace('/', '')
    parent_id = build_api_gateway_root_resource_id_ref(api_name=rest_api)
    rest_api_id = build_rest_api_id_ref(api_name=rest_api)
    resource = {
        resource_name:
            {
                "parent_id": parent_id,
                "path_part": resource_name,
                "rest_api_id": rest_api_id
            }
    }
    return resource


def api_gateway_method_response(method_name, status_code, http_method,
                                resource_name, api_name):
    response_name = f'{resource_name}_{http_method}_{status_code}_method_response'
    method = build_method_name_reference(method_name=method_name)
    resource_id = build_resource_id_ref(resource_name=resource_name)
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
    resource_id = build_resource_id_ref(resource_name=resource_name)
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    http_method = build_method_name_reference(method_name)

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


def api_gateway_stage(api_name, stage_name, deployment_name):
    rest_api_id = build_rest_api_id_ref(api_name=api_name)
    deployment_id = build_api_gateway_deployment_id_ref(
        deployment_name=deployment_name)
    resource = {
        stage_name:
            {
                "deployment_id": deployment_id,
                "rest_api_id": rest_api_id,
                "stage_name": stage_name
            }
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
    integration_response_name = f'{resource_name}_{http_method}_{status_code}_integration_response'
    method = build_method_name_reference(method_name)
    resource_id = build_resource_id_ref(resource_name=resource_name)
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
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'

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
