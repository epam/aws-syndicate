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
from secrets import token_hex
from typing import Optional

from boto3 import client
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

RESPONSE_PARAM_ALLOW_ORIGIN = \
    "method.response.header.Access-Control-Allow-Origin"
RESPONSE_PARAM_ALLOW_METHODS = \
    "method.response.header.Access-Control-Allow-Methods"
RESPONSE_PARAM_ALLOW_HEADERS = \
    "method.response.header.Access-Control-Allow-Headers"

REQ_VALIDATOR_PARAM_VALIDATE_PARAMS = 'validateRequestParameters'
REQ_VALIDATOR_PARAM_VALIDATE_BODY = 'validateRequestBody'
REQ_VALIDATOR_PARAM_NAME = 'name'

_LOG = get_logger('syndicate.connection.api_gateway_connection')


@apply_methods_decorator(retry())
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

    def create_rest_api(self, api_name,
                        binary_media_types=None,
                        description=None,
                        clone_from=None):
        """
        :type api_name: str
        :type description: str
        :type binary_media_types: list
        :type clone_from: str
        :param clone_from: The ID of the RestApi that you want to clone from.
        """
        params = dict(name=api_name)
        if description:
            params['description'] = description
        if clone_from:
            params['cloneFrom'] = clone_from
        if binary_media_types:
            params['binaryMediaTypes'] = binary_media_types
        return self.client.create_rest_api(**params)

    def create_openapi(self, openapi_context):
        # Create a new API Gateway with the OpenAPI definition
        try:
            response = self.client.import_rest_api(
                body=json.dumps(openapi_context),
                failOnWarnings=False
            )
            api_id = response['id']
            _LOG.debug(f"API Gateway created successfully with ID: {api_id}")
            return api_id
        except self.client.exceptions.ClientError as e:
            _LOG.error(f"An error occurred: {e}")
            return None

    def describe_openapi(self, api_id, stage_name):
        try:
            response = self.client.get_export(
                restApiId=api_id,
                stageName=stage_name,
                exportType='oas30',
                parameters={
                    'extensions': 'integrations,authorizers,apigateway'},
                accepts='application/json'
            )
            return response
        except self.client.exceptions.NotFoundException:
            _LOG.error(f"Not found api with id: {api_id}")
            return None

    def update_openapi(self, api_id, openapi_context):
        # Update the API Gateway with the OpenAPI definition
        try:
            self.client.put_rest_api(
                restApiId=api_id,
                mode='overwrite',
                body=json.dumps(openapi_context),
                failOnWarnings=False
            )
            _LOG.debug("API Gateway updated successfully.")
        except self.client.exceptions.ClientError as e:
            _LOG.error(f"An error occurred: {e}")

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
            params['requestValidatorId'] = request_validator
        self.client.put_method(**params)

    def create_request_validator(self, api_id, name: str = None,
                                 validate_request_body: bool = False,
                                 validate_request_parameters: bool = False):
        """
        Helper function to create a request validator. Returns its id
        :type api_id: str
        :param api_id: Identifier of the associated RestApi.
        :type name: str
        :param name: name of request validator. If not set, will be generated
        :type validate_request_body: bool = False
        :param validate_request_body: whether to validate request body
        :type validate_request_parameters: bool = False
        :param validate_request_parameters: whether to validate query params
        :return: str, identifier of created RequestValidator.
        """
        params = dict(
            restApiId=api_id,
            name=name or f'default-validator-name-{token_hex(8)}',
            validateRequestBody=validate_request_body,
            validateRequestParameters=validate_request_parameters)
        return self.client.create_request_validator(**params)['id']

    @staticmethod
    def get_request_validator_params(request_validator):
        try:
            validator_name = request_validator.pop('name')
        except KeyError:  # not critical error
            validator_name = None
        request_validator_params = {}

        if ('validate_request_body', True) in request_validator.items():
            request_validator_params.update(
                {REQ_VALIDATOR_PARAM_VALIDATE_BODY: True,
                 REQ_VALIDATOR_PARAM_NAME: 'Validate body'})
        if ('validate_request_parameters', True) in request_validator.items():
            request_validator_params.update(
                {REQ_VALIDATOR_PARAM_VALIDATE_PARAMS: True,
                 REQ_VALIDATOR_PARAM_NAME: 'Validate query string '
                                           'parameters and headers'})

        # Need an additional check for validator name.
        # If the user wants to validate both the body and the parameters,
        # the number of 'request_validator_params' parameters will be equal
        # to three
        SETTED_PARAMETERS = 3

        if len(request_validator_params) == SETTED_PARAMETERS:
            request_validator_params.update(
                {REQ_VALIDATOR_PARAM_NAME: 'Validate body, query '
                                           'string parameters, '
                                           'and headers'})
        if validator_name:
            request_validator_params.update(
                {REQ_VALIDATOR_PARAM_NAME: validator_name})
        return request_validator_params

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
                                  cache_key_parameters=None,
                                  request_parameters=None):
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
        :type request_parameters: dict
        :param request_parameters: A key-value map specifying request parameters
         (path, query string, header)
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
        if request_parameters:
            params['request_parameters'] = request_parameters
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

        credentials = ApiGatewayConnection.get_service_integration_credentials(
            acc_id, role
        )

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

    @staticmethod
    def get_service_integration_credentials(acc_id, role):
        return 'arn:aws:iam::*:user/*' if role == 'caller_identity' \
            else 'arn:aws:iam::{0}:role/{1}'.format(acc_id, role)

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
        self.create_method(api_id, resource_id, 'OPTIONS')
        self.create_integration(api_id=api_id, resource_id=resource_id,
                                method='OPTIONS', int_type='MOCK',
                                request_templates={
                                    'application/json': '{"statusCode": 200}'
                                })

        self.create_method_response(
            api_id, resource_id, 'OPTIONS', response_parameters={
                RESPONSE_PARAM_ALLOW_HEADERS: False,
                RESPONSE_PARAM_ALLOW_METHODS: False,
                RESPONSE_PARAM_ALLOW_ORIGIN: False
            })
        content_types = ("'Content-Type,X-Amz-Date,Authorization,X-Api-Key,"
                         "X-Amz-Security-Token'")
        self.create_integration_response(
            api_id, resource_id, 'OPTIONS', response_parameters={
                RESPONSE_PARAM_ALLOW_HEADERS: content_types,
                RESPONSE_PARAM_ALLOW_METHODS: "\'*\'",
                RESPONSE_PARAM_ALLOW_ORIGIN: "\'*\'"
            })

    def deploy_api(self, api_id, stage_name, stage_description='',
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

    def get_authorizer(self, rest_api_id, authorizer_id):
        return self.client.get_authorizer(restApiId=rest_api_id,
                                          authorizerId=authorizer_id)

    def update_compression_size(self, rest_api_id, compression_size=None):
        """Enables api compression and sets minimum compression size equal
        to given param. If the param wasn't given, will be disabled"""
        patchOperation = {
            'op': 'replace',
            'path': '/minimumCompressionSize',
        }
        if compression_size:
            patchOperation['value'] = str(compression_size)
            _LOG.debug(f'Setting compression size to "{compression_size}"')
        params = dict(restApiId=rest_api_id)
        params['patchOperations'] = [patchOperation, ]
        _LOG.debug(f'Updating rest api with params: "{params}"')
        return self.client.update_rest_api(**params)

    def create_model(self, rest_api_id, name, content_type, description=None,
                     schema=None):
        """Adds a new Model resource to an existing RestApi resource."""
        _LOG.debug(f'Creating new model "{name}"')
        params = {
            'contentType': content_type,
            'restApiId': rest_api_id,
            'name': name
        }
        if description:
            params['description'] = description
        if schema:
            params['schema'] = schema
        return self.client.create_model(**params)

    def delete_model(self, rest_api_id, name):
        _LOG.debug(f'Deleting model "{name}"')
        return self.client.delete_model(restApiId=rest_api_id, modelName=name)

    def get_model(self, rest_api_id, name, flatten=False):
        try:
            return self.client.get_model(restApiId=rest_api_id, modelName=name,
                                         flatten=flatten)
        except ClientError as e:
            if 'NotFoundException' in str(e):
                _LOG.warn(f'Cannot find model "{name}"')
                return None
            else:
                raise e


class ApiGatewayV2Connection:
    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self._region = region
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._client: Optional[BaseClient] = None

    @property
    def client(self) -> BaseClient:
        if not self._client:
            self._client = client(
                'apigatewayv2', self._region,
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                aws_session_token=self._aws_session_token
            )
            _LOG.debug('Opened new API Gateway connection.')
        return self._client

    def create_web_socket_api(self, name: str,
                              route_selection_expression: Optional[
                                  str] = 'request.body.action') -> str:
        return self.client.create_api(
            Name=name,
            ProtocolType='WEBSOCKET',
            RouteSelectionExpression=route_selection_expression
        )['ApiId']

    def create_stage(self, api_id: str, stage_name: str):
        return self.client.create_stage(
            ApiId=api_id,
            AutoDeploy=True,
            StageName=stage_name
        )

    # def create_deployment(self, api_id: str, stage_name: str):
    #     return self.client.create_deployment(
    #         ApiId=api_id,
    #         StageName=stage_name
    #     )

    def get_api_by_name(self, name: str) -> Optional[dict]:
        return next((api for api in self.client.get_apis()['Items']
                     if api['Name'] == name), None)

    def get_route_id_by_name(self, api_id: str, name: str) -> Optional[str]:
        return next(
            (route['RouteId'] for route in
             self.client.get_routes(ApiId=api_id)['Items']
             if route['RouteKey'] == name), None
        )

    def delete_api(self, api_id: str):
        return self.client.delete_api(
            ApiId=api_id
        )

    def create_lambda_integration(self, api_id: str, lambda_arn: str,
                                  enable_proxy: Optional[bool] = False) -> str:
        integration_uri = \
            f'arn:aws:apigateway:{self.client.meta.region_name}:lambda:path/' \
            f'2015-03-31/functions/{lambda_arn}/invocations'
        return self.client.create_integration(
            ApiId=api_id,
            IntegrationType='AWS_PROXY' if enable_proxy else 'AWS',
            IntegrationMethod='POST',
            IntegrationUri=integration_uri
        )['IntegrationId']

    def put_route_integration(self, api_id: str, route_name: str,
                              integration_id: str) -> str:
        route_id = self.get_route_id_by_name(api_id, route_name)
        if route_id:  # already exists
            self.client.update_route(
                ApiId=api_id,
                RouteId=route_id,
                Target=f'integrations/{integration_id}'
            )
        else:  # not route_id, does not exist
            response = self.client.create_route(
                ApiId=api_id,
                RouteKey=route_name,
                Target=f'integrations/{integration_id}'
            )
            route_id = response['RouteId']
        return route_id

    def get_routes(self, api_id: str):
        return self.client.get_routes(ApiId=api_id)

    def get_integration(self, api_id: str, integration_id: str):
        integration = self.client.get_integration(ApiId=api_id,
                                                  IntegrationId=integration_id)

        if integration.get('IntegrationMethod') == 'POST' and \
                integration.get('IntegrationUri'):
            return integration['IntegrationUri'].split('functions/')[-1].\
                replace('/invocations', '')
