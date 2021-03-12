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
from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.api_gateway_connection')


@apply_methods_decorator(retry)
class ApiGatewayConnection(object):
    """ API Gateway connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('apigateway', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new API Gateway connection.')

    def create_rest_api(self, api_name, description=None, clone_from=None):
        """
        :type api_name: str
        :type description: str
        :type clone_from: str
        :param clone_from: The ID of the RestApi that you want to clone from.
        """
        params = dict(name=api_name)
        if description:
            params['description'] = description
        if clone_from:
            params['cloneFrom'] = clone_from
        return self.client.create_rest_api(**params)

    def remove_api(self, api_id):
        """
        :type api_id: str
        """
        self.client.delete_rest_api(restApiId=api_id)

    def get_api_by_name(self, api_name):
        """
        :type api_name: str
        """
        apis = self.get_all_apis()
        if apis:
            for each in apis:
                if each['name'] == api_name:
                    return each

    def get_api_id(self, api_name):
        """
        :type api_name: str
        """
        api_info = self.get_api_by_name(api_name)
        if api_info:
            return api_info['id']

    def get_resource_id(self, api_id, resource_path):
        """
        :type api_id: str
        :type resource_path: str
        """
        resource_info = self.get_resource_by_path(api_id, resource_path)
        if resource_info:
            return resource_info['id']

    def get_resource_by_path(self, api_id, resource_path):
        """
        :type api_id: str
        :type resource_path: str
        """
        if not api_id:
            return
        resources = []
        response = self.client.get_resources(restApiId=api_id, limit=100)
        if response.get('items'):
            resources.extend(response.get('items'))
        token = response.get('position')
        while token:
            response = self.client.get_resources(restApiId=api_id, limit=100,
                                                 position=token)
            if response.get('items'):
                resources.extend(response.get('items'))
            token = response.get('position')
        for each in resources:
            if each['path'] == resource_path:
                return each

    def get_resources(self, api_id):
        resources = []
        response = self.client.get_resources(restApiId=api_id)
        if response.get('items'):
            resources.extend(response.get('items'))
        token = response.get('position')
        while token:
            response = self.client.get_resources(restApiId=api_id,
                                                 position=token)
            if response.get('items'):
                resources.extend(response.get('items'))
            token = response.get('position')
        return resources

    def get_method(self, api_id, resource_id, method):
        """
        :type api_id: str
        :type resource_id: str
        :type method: str
        """
        res = self.client.get_resource(restApiId=api_id,
                                       resourceId=resource_id)
        methods = res.get('resourceMethods')
        if methods and method in methods:
            return True

    def create_resource(self, api_id, resource_path):
        """
        :type api_id: str
        :type resource_path: str
        """
        initial_resource = '/'
        parent_resource_id = self.get_resource_id(api_id, initial_resource)
        _LOG.debug('Processing resource %s, parent id - %s', initial_resource,
                   parent_resource_id)
        if resource_path.startswith('/'):
            resource_path = resource_path[1:]
        resource_path_split = resource_path.split('/')
        for resource in resource_path_split:
            try:
                _LOG.debug('Processing parent id: %s', parent_resource_id)
                resp = self.client.create_resource(restApiId=api_id,
                                                   parentId=parent_resource_id,
                                                   pathPart=resource)
                resource_id = resp['id']
            except ClientError as e:
                resource_id = None
                if 'ConflictException' in str(e):
                    _LOG.debug('Error while creating resource {0}.'
                               ' Creation stage: {1}.'
                               .format(resource_path, resource))
                    resource_info = self.get_resource_by_path(
                        api_id, initial_resource + resource)
                    if resource_info:
                        resource_id = resource_info['id']
                if not resource_id:
                    raise e
            parent_resource_id = resource_id
            initial_resource += resource
            initial_resource += '/'

    def create_method(self, api_id, resource_id, method,
                      authorization_type=None, authorizer_id=None,
                      api_key_required=None, request_parameters=None,
                      request_models=None,
                      request_validator=None):
        """
        :type api_id: str
        :type resource_id: str
        :type method: str
        :param method: Specifies the method request's HTTP method type.
        :type authorization_type: str
        :param authorization_type: Specifies the type of authorization used for
        the method.
        :type authorizer_id: str
        :param authorizer_id: Specifies the identifier of an Authorizer to use
        on this Method, if the type is CUSTOM.
        :type api_key_required: bool
        :param api_key_required: Specifies whether the method required a valid
        ApiKey .
        :type request_parameters: dict
        :param request_parameters: A key-value map defining required or
        optional method request parameters that can be accepted by API Gateway.
        {'string': True|False}. Boolean flag - required parameter or optional.
        :type request_models: dict
        :param request_models: Specifies the Model resources used for the
        request's content type. Request models are represented as a key/value
        map, with a content type as the key and a Model name as the value.
        {'string': 'string'}
        :type request_validator: dict
        :param request_validator: Dictionary with values to create request
        validator. It could contains name of validator and validate parameters
        (validate_request_body, validate_request_parameters or both).
        """
        params = dict(restApiId=api_id, resourceId=resource_id,
                      httpMethod=method, authorizationType='NONE',
                      apiKeyRequired=False)
        if authorization_type:
            params['authorizationType'] = authorization_type
        if authorizer_id:
            params['authorizerId'] = authorizer_id
        if api_key_required:
            params['apiKeyRequired'] = api_key_required
        if request_parameters:
            params['requestParameters'] = request_parameters
        if request_models:
            params['requestModels'] = request_models
        if request_validator:
            params['requestValidatorId'] = self.create_request_validator(
                api_id, request_validator)
        self.client.put_method(**params)

    def create_request_validator(self, api_id, request_validator):
        """
        Helper function to create a request validator. Returns its id.

        :type api_id: str
        :param api_id: Identifier of the associated RestApi.
        :type request_validator: dict
        :param request_validator: Dictionary with values to create request
        validator. It could contains name of validator and validate parameters
        (validate_request_body, validate_request_parameters or both)
        :return: str, identifier of created RequestValidator.
        """
        try:
            validator_name = request_validator.pop('name')
        except KeyError:  # not critical error
            validator_name = None

        request_validator_params = {}

        if ('validate_request_body', True) in request_validator.items():
            request_validator_params.update({'validateRequestBody': True,
                                             'name': 'Validate body'})
        if ('validate_request_parameters', True) in request_validator.items():
            request_validator_params.update({'validateRequestParameters': True,
                                             'name': 'Validate query string '
                                                     'parameters and headers'})

        # Need an additional check for validator name.
        # If the user wants to validate both the body and the parameters,
        # the number of 'request_validator_params' parameters will be equal
        # to three
        SETTED_PARAMETERS = 3

        if len(request_validator_params) == SETTED_PARAMETERS:
            request_validator_params.update({'name': 'Validate body, query '
                                                     'string parameters, '
                                                     'and headers'})
        if validator_name:
            request_validator_params.update({'name': validator_name})

        request_validator_id = self.client.create_request_validator(
            restApiId=api_id, **request_validator_params)['id']
        return request_validator_id

    def create_integration(self, api_id, resource_id, method, int_type,
                           integration_method=None, uri=None, credentials=None,
                           request_parameters=None, request_templates=None,
                           passthrough_behavior=None, cache_namespace=None,
                           cache_key_parameters=None):
        params = dict(restApiId=api_id, resourceId=resource_id, type=int_type,
                      httpMethod=method)
        if integration_method:
            params['integrationHttpMethod'] = integration_method
        if uri:
            params['uri'] = uri
        if credentials:
            params['credentials'] = credentials
        if request_parameters:
            params['requestParameters'] = request_parameters
        if request_templates:
            params['requestTemplates'] = request_templates
        if passthrough_behavior:
            params['passthroughBehavior'] = passthrough_behavior
        if cache_namespace:
            params['cacheNamespace'] = cache_namespace
        if cache_key_parameters:
            params['cacheKeyParameters'] = cache_key_parameters
        self.client.put_integration(**params)

    def create_lambda_integration(self, lambda_arn, api_id, resource_id,
                                  method, request_templates=None,
                                  passthrough_behavior=None,
                                  credentials=None,
                                  enable_proxy=False,
                                  cache_key_parameters=None):
        """ Create API Gateway integration with lambda by name.

        :type lambda_arn: str
        :type api_id: str
        :type resource_id: str
        :type method: str
        :type request_templates: dict
        :type passthrough_behavior: str
        :param passthrough_behavior: WHEN_NO_MATCH , WHEN_NO_TEMPLATES , NEVER
        :type lambda_region: str
        :type credentials: str
        :param credentials: role arn
        """
        uri = ('arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions/{1}'
               '/invocations').format(self.region, lambda_arn)

        int_type = 'AWS_PROXY' if enable_proxy else 'AWS'

        params = dict(int_type=int_type, integration_method='POST',
                      method=method, passthrough_behavior='WHEN_NO_MATCH',
                      uri=uri, api_id=api_id, resource_id=resource_id)
        if credentials:
            params['credentials'] = credentials
        if passthrough_behavior:
            params['passthrough_behavior'] = passthrough_behavior
        if request_templates:
            params['request_templates'] = request_templates
        if cache_key_parameters:
            params['cache_key_parameters'] = cache_key_parameters
        self.create_integration(**params)

    def create_service_integration(self, acc_id, api_id, resource_id,
                                   method, integration_method, role,
                                   action, request_templates=None,
                                   passthrough_behavior=None,
                                   request_parameters=None):
        """
        Create API Gateway integration with AWS service.

        :type acc_id: str
        :param acc_id: Account id
        :type api_id: str
        :param api_id: Identifier of the RestApi
        :type resource_id: str
        :param resource_id: Request's resource ID
        :type method: str
        :param method: Request's HTTP method
        :type integration_method: str
        :param integration_method: Integration HTTP method
        :type role: str
        :param role: Execution role
        :type action: str
        :param action: using for URI, general template:
        {region}:{subdomain.service|service}:path|action/{service_api}
        :type request_templates: dict
        :param request_templates: A key-value map where content type is a key
        and the template is the value
        :type passthrough_behavior: str
        :param passthrough_behavior: WHEN_NO_MATCH , WHEN_NO_TEMPLATES , NEVER
        :type request_parameters: dict
        :param request_parameters: A key-value map specifying request parameters
         (path, query string, header)
        """
        uri = 'arn:aws:apigateway:{0}'.format(action)

        credentials = 'arn:aws:iam::*:user/*' if role == 'caller_identity' \
            else 'arn:aws:iam::{0}:role/{1}'.format(acc_id, role)

        params = dict(int_type='AWS', integration_method=integration_method,
                      method=method, passthrough_behavior='WHEN_NO_MATCH',
                      uri=uri, api_id=api_id, resource_id=resource_id,
                      credentials=credentials)

        if passthrough_behavior:
            params['passthrough_behavior'] = passthrough_behavior
        if request_templates:
            params['request_templates'] = request_templates
        if request_parameters:
            params['request_parameters'] = request_parameters
        self.create_integration(**params)

    def create_mock_integration(self, api_id, resource_id, method,
                                request_templates=None,
                                passthrough_behavior=None):
        params = dict(int_type='MOCK', method=method, api_id=api_id,
                      resource_id=resource_id)
        if passthrough_behavior:
            params['passthrough_behavior'] = passthrough_behavior
        if request_templates:
            params['request_templates'] = request_templates
        self.create_integration(**params)

    def create_http_integration(self, api_id, resource_id,
                                method, integration_method, uri,
                                request_templates=None,
                                passthrough_behavior=None, enable_proxy=False):

        int_type = 'HTTP_PROXY' if enable_proxy else 'HTTP'

        params = dict(int_type=int_type, integration_method=integration_method,
                      method=method, passthrough_behavior='WHEN_NO_MATCH',
                      uri=uri, api_id=api_id, resource_id=resource_id)

        if passthrough_behavior:
            params['passthrough_behavior'] = passthrough_behavior
        if request_templates:
            params['request_templates'] = request_templates
        self.create_integration(**params)

    def create_integration_response(self, api_id, resource_id, method,
                                    status_code=None, selection_pattern=None,
                                    response_parameters=None,
                                    response_templates=None,
                                    enable_cors=False):
        """
        :type api_id: str
        :type resource_id: str
        :type method: str
        :param method: Specifies the method request's HTTP method type.
        :type status_code: str
        :type selection_pattern: str
        :type response_parameters: dict
        :type response_templates: dict
        :type enable_cors: bool
        """
        response_allow_origin = "response.header.Access-Control-Allow-Origin"
        method_allow_origin = "method.{0}".format(response_allow_origin)
        params = dict(restApiId=api_id, httpMethod=method, statusCode='200',
                      resourceId=resource_id,
                      responseTemplates={'application/json': ''})
        if enable_cors:
            params['responseParameters'] = {method_allow_origin: "\'*\'"}
        if selection_pattern:
            params['selectionPattern'] = selection_pattern
        if status_code:
            params['statusCode'] = status_code
        if response_parameters:
            if enable_cors:
                response_parameters[method_allow_origin] = "\'*\'"
            params['responseParameters'] = response_parameters
        if response_templates:
            params['responseTemplates'] = response_templates
        self.client.put_integration_response(**params)

    def create_method_response(self, api_id, resource_id, method,
                               status_code=None, response_parameters=None,
                               response_models=None, enable_cors=False):
        """
        :type api_id: str
        :type resource_id: str
        :type method: str
        :param method: Specifies the method request's HTTP method type.
        :type status_code: str
        :type response_parameters: dict
        :type response_models: dict
        :type enable_cors: bool
        """
        response_allow_origin = "response.header.Access-Control-Allow-Origin"
        method_allow_origin = "method.{0}".format(response_allow_origin)
        params = dict(restApiId=api_id, resourceId=resource_id,
                      httpMethod=method, statusCode='200',
                      responseModels={'application/json': 'Empty'})
        if enable_cors:
            params['responseParameters'] = {method_allow_origin: False}
        if status_code:
            params['statusCode'] = status_code
        if response_parameters:
            if enable_cors:
                response_parameters[method_allow_origin] = False
            params['responseParameters'] = response_parameters
        if response_models:
            params['responseModels'] = response_models
        self.client.put_method_response(**params)

    def enable_cors_for_resource(self, api_id, resource_id):
        """ When your API's resources receive requests from a domain other than
        the API's own domain, you must enable cross-origin resource sharing
        (CORS) for selected methods on the resource.

        :type api_id: str
        :type resource_id: str
        """
        allow_headers = "method.response.header.Access-Control-Allow-Headers"
        allow_methods = "method.response.header.Access-Control-Allow-Methods"
        allow_origin = "method.response.header.Access-Control-Allow-Origin"
        self.create_method(api_id, resource_id, 'OPTIONS')
        self.create_integration(api_id=api_id, resource_id=resource_id,
                                method='OPTIONS', int_type='MOCK',
                                request_templates={
                                    'application/json': '{"statusCode": 200}'
                                })

        self.create_method_response(
            api_id, resource_id, 'OPTIONS', response_parameters={
                allow_headers: False,
                allow_methods: False,
                allow_origin: False
            })
        content_types = ("'Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                         "X-Amz-Security-Token'")
        self.create_integration_response(
            api_id, resource_id, 'OPTIONS', response_parameters={
                allow_headers: content_types,
                allow_methods: "\'*\'",
                allow_origin: "\'*\'"
            })

    def deploy_api(self, api_id, stage_name='prod', stage_description='',
                   description='', cache_cluster_enabled=False,
                   cache_cluster_size=None, variables=None):
        """
        :type api_id: str
        :type stage_name: str
        :type stage_description: str
        :param stage_name:
        :param stage_description:
        :param description:
        :param cache_cluster_enabled:
        :param cache_cluster_size: '0.5'|'1.6'|'6.1'|'13.5'|'28.4'|'58.2'|'118'
        |'237'
        :type cache_cluster_size: str
        :type variables: dict
        """
        params = dict(restApiId=api_id, stageName=stage_name)
        if stage_description:
            params['stageDescription'] = stage_description
        if description:
            params['description'] = description
        if cache_cluster_enabled:
            params['cacheClusterEnabled'] = cache_cluster_enabled
        if cache_cluster_size:
            params['cacheClusterSize'] = cache_cluster_size
        if variables:
            params['variables'] = variables
        self.client.create_deployment(**params)

    def get_all_apis(self):
        """ Get all existing APIs."""
        existing_apis = []
        response = self.client.get_rest_apis()
        existing_apis.extend(response.get('items'))
        token = response.get('position')
        while token:
            response = self.client.get_rest_apis(position=token)
            existing_apis.extend(response.get('items'))
            token = response.get('position')
        return existing_apis

    def get_api(self, api_id):
        return self.client.get_rest_api(restApiId=api_id)

    def get_gateway_responses(self, api_id):
        return self.client.get_gateway_responses(restApiId=api_id).get('items',
                                                                       [])

    def add_header_to_gateway_response(self, api_id, response_type, name,
                                       value):
        path = '/responseParameters/gatewayresponse.header.' + name

        operation = {
            'op': 'add',
            'path': path,
            'value': value
        }
        _LOG.info(
            'Update Gateway response context: api_id:{0}; '
            'response_type:{1}; name:{2}; operation:{3};'.format(
                api_id, response_type, name, operation))

        return self.client.update_gateway_response(restApiId=api_id,
                                                   responseType=response_type,
                                                   patchOperations=[operation])

    def generate_sdk(self, api_id, stage_name='prod', sdk_type='javascript'):
        """ generates sdk of given type for specified stage of api gateway
        :param api_id: api gateway name
        :type api_id: str
        :param stage_name: stage name
        :type stage_name" str
        :param sdk_type: sdk type, possible values: javascript, android,
        objective c
        :type sdk_type: str
        """
        return self.client.get_sdk(restApiId=api_id, stageName=stage_name,
                                   sdkType=sdk_type)

    def update_configuration(self, rest_api_id, stage_name,
                             patch_operations):
        return self.client.update_stage(
            restApiId=rest_api_id,
            stageName=stage_name,
            patchOperations=patch_operations
        )

    def create_authorizer(self, api_id, name, type, provider_arns=None,
                          auth_type=None, authorizer_uri=None,
                          authorizer_credentials=None, identity_source=None,
                          validation_expression=None, ttl=None):
        params = dict(restApiId=api_id, name=name, type=type)
        if provider_arns:
            params['providerARNs'] = provider_arns
        if auth_type:
            params['authType'] = auth_type
        if authorizer_uri:
            params['authorizerUri'] = authorizer_uri
        if authorizer_credentials:
            params['authorizerCredentials'] = authorizer_credentials
        if identity_source:
            params['identitySource'] = identity_source
        if validation_expression:
            params['identityValidationExpression'] = validation_expression
        if ttl:
            params['authorizerResultTtlInSeconds'] = ttl

        return self.client.create_authorizer(**params)

    def get_authorizers(self, api_id):
        items = []
        params = dict(restApiId=api_id)
        response = self.client.get_authorizers(**params)
        if response.get('items'):
            items.extend(response.get('items'))
        position = response.get('position')
        while position:
            params['position'] = position
            response = self.client.get_authorizers(**params)
            if response.get('items'):
                items.extend(response.get('items'))
            position = response.get('position')
        return items
