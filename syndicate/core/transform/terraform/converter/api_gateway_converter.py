from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter

AVAILABLE_METHODS = ['GET', 'PUT', 'POST', 'OPTIONS', 'DELETE',
                     'HEAD', 'PATCH', 'ANY']


class ApiGatewayConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        api_name = resource.get('resource_name')
        authorizers = resource.get('authorizers')
        dependencies = resource.get('dependencies')
        auth_type = authorizers.get('type')
        lambda_name = authorizers.get('lambda_name')
        ttl = authorizers.get('ttl')

        rest_api_template = generate_tf_template_for_api_gateway_api(
            api_name=api_name)
        self.template.add_aws_api_gateway_rest_api(meta=rest_api_template)

        method_names = []
        integration_names = []
        resources = resource.get('resources')
        for res_name, res in resources.items():
            api_gateway_resource = get_api_gateway_resource(path_part=res_name,
                                                            rest_api=api_name)
            self.template.add_aws_api_gateway_resource(
                meta=api_gateway_resource)
            for http_method in AVAILABLE_METHODS:
                method_config = res.get(http_method)
                if method_config:
                    resource_name = res_name.replace('/', '')

                    method_name = f'{resource_name}-{http_method}'
                    method_names.append(method_name)
                    method_template = get_api_gateway_method(
                        http_method=http_method,
                        resource_name=resource_name,
                        rest_api=api_name,
                        authorization='NONE',
                        method_name=method_name)
                    self.template.add_aws_api_gateway_method(
                        meta=method_template)

                    lambda_alias = method_config.get('lambda_alias')
                    authorization_type = method_config.get(
                        'authorization_type')
                    method_request_parameters = method_config.get(
                        'method_request_parameters')
                    lambda_name = method_config.get('lambda_name')
                    integration_type = method_config.get('integration_type')
                    integration_request_template = method_config.get(
                        'integration_request_body_template')

                    integration_name = f'{resource_name}_{http_method}_integration'
                    integration_names.append(integration_name)
                    integration = api_gateway_integration(
                        integration_name=integration_name,
                        api_name=api_name,
                        http_method=http_method,
                        resource_name=resource_name,
                        integration_type='AWS',
                        lambda_name=lambda_name,
                        request_template=integration_request_template)
                    self.template.add_aws_api_gateway_integration(
                        meta=integration)

                    responses = method_config.get('responses')
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

                    integration_responses = method_config.get(
                        'integration_responses')
                    for int_response in integration_responses:
                        status_code = int_response.get('status_code')
                        response_templates = int_response.get(
                            'response_templates')
                        error_regex = int_response.get('error_regex')
                        integration_response = api_gateway_integration_response(
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


def generate_tf_template_for_api_gateway_api(api_name):
    resource = {
        api_name: [
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
        ]
    }
    return resource


def get_api_gateway_resource(path_part, rest_api):
    resource_name = path_part.replace('/', '')
    parent_id = '${aws_api_gateway_rest_api.' + rest_api + '.root_resource_id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
    resource = {
        resource_name: [
            {
                "parent_id": parent_id,
                "path_part": resource_name,
                "rest_api_id": rest_api_id
            }
        ]
    }
    return resource


def api_gateway_method_response(method_name, status_code, http_method,
                                resource_name, api_name):
    response_name = f'{resource_name}_{http_method}_{status_code}_method_response'
    method = '${aws_api_gateway_method.' + method_name + '.http_method}'
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
    resource = {
        response_name: [
            {
                "http_method": method,
                "resource_id": resource_id,
                "rest_api_id": rest_api_id,
                "status_code": status_code
            }
        ]
    }
    return resource


def api_gateway_integration(integration_name, api_name, resource_name,
                            http_method, integration_type, lambda_name,
                            request_template):
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
    uri = '${aws_lambda_function.' + lambda_name + '.invoke_arn}'
    resource = {
        integration_name: [
            {
                "http_method": http_method,
                "resource_id": resource_id,
                "rest_api_id": rest_api_id,
                "type": integration_type,
                "integration_http_method": 'POST',
                "uri": uri,
                "request_templates": request_template
            }
        ]
    }
    return resource


def api_gateway_stage(api_name, stage_name, deployment_name):
    rest_api_id = "${aws_api_gateway_rest_api." + api_name + ".id}"
    deployment_name = '${aws_api_gateway_deployment.' + deployment_name + '.id}'
    resource = {
        stage_name: [
            {
                "deployment_id": deployment_name,
                "rest_api_id": rest_api_id,
                "stage_name": stage_name
            }
        ]
    }
    return resource


def api_gateway_deployment(api_name, deployment_name, methods,
                           integration_names):
    dependencies = []
    for method in methods:
        dependencies.append(f'aws_api_gateway_method.{method}')
    for integration in integration_names:
        dependencies.append(f'aws_api_gateway_integration.{integration}')

    rest_api_id = "${aws_api_gateway_rest_api." + api_name + ".id}"
    resource = {
        deployment_name: [
            {
                "rest_api_id": rest_api_id,
                "depends_on": dependencies
            }
        ]
    }
    return resource


def api_gateway_integration_response(resource_name, api_name,
                                     status_code, response_template,
                                     http_method, method_name, integration,
                                     selection_pattern=None):
    integration_response_name = f'{resource_name}_{http_method}_{status_code}_integration_response'
    method = '${aws_api_gateway_method.' + method_name + '.http_method}'
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
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
                           authorization='NONE'):
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
    resource = {
        method_name: [
            {
                "authorization": authorization,
                "http_method": http_method,
                "resource_id": resource_id,
                "rest_api_id": rest_api_id
            }
        ]
    }
    return resource


def get_api_gateway_stage(stage_name, deployment, rest_api):
    deployment_id = '${aws_api_gateway_deployment.' + deployment + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
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
