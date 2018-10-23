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
from syndicate.core import CONFIG, CONN
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
from syndicate.core.resources.lambda_resource import (
    resolve_lambda_arn_by_version_and_alias)

SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']

_LOG = get_logger('syndicate.core.resources.api_gateway_resource')

_DEFAULT_RESPONSES = {
    "responses": [
        {
            "status_code": "200"
        },
        {
            "status_code": "400"
        },
        {
            "status_code": "401"
        },
        {
            "status_code": "403"
        },
        {
            "status_code": "406"
        },
        {
            "status_code": "404"
        },
        {
            "status_code": "500"
        },
        {
            "status_code": "503"
        }
    ],
    "integration_responses": [
        {
            "status_code": "200"
        },
        {
            "status_code": "400",
            "error_regex": ".*ERROR_CODE\\\": 400.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "401",
            "error_regex": ".*ERROR_CODE\\\": 401.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "403",
            "error_regex": ".*ERROR_CODE\\\": 403.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "404",
            "error_regex": ".*ERROR_CODE\\\": 404.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "406",
            "error_regex": ".*ERROR_CODE\\\": 406.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "500",
            "error_regex": ".*ERROR_CODE\\\": 500.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        },
        {
            "status_code": "503",
            "error_regex": ".*ERROR_CODE\\\": 503.*",
            'response_templates': {
                'application/json': '#set ($errorMessageObj = $util.parseJson('
                                    '$input.path(\'$.errorMessage\')))'
                                    '{"message" : "$errorMessageObj.message"}'
            }
        }
    ]
}

_CORS_HEADER_NAME = 'Access-Control-Allow-Origin'
_CORS_HEADER_VALUE = "'*'"

_API_GATEWAY_CONN = CONN.api_gateway()
_LAMBDA_CONN = CONN.lambda_conn()


def api_resource_identifier(name):
    return _API_GATEWAY_CONN.get_api_id(name)


def create_api_gateway(args):
    """ Create api gateway in pool in sub processes.

    :type args: list
    """
    return create_pool(_create_api_gateway_from_meta, 3, args)


def _escape_path(parameter):
    index = parameter.find('/', 0)
    if index == -1:
        return parameter
    parameter = parameter[:index] + '~1' + parameter[index + 1:]
    return _escape_path(parameter)


def configure_cache(api_id, stage_name, api_resources):
    for resource_path, resource_meta in api_resources.iteritems():
        for method_name, method_meta in resource_meta.iteritems():
            if method_name in SUPPORTED_METHODS:
                cache_configuration = method_meta.get('cache_configuration')
                if not cache_configuration:
                    continue
                cache_ttl_setting = cache_configuration.get('cache_ttl_sec')
                if cache_ttl_setting:
                    _LOG.info(
                        'Configuring cache for {0}; TTL: {1}'.format(
                            resource_path, cache_ttl_setting))
                    escaped_resource = _escape_path(resource_path)
                    _API_GATEWAY_CONN.update_configuration(
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
def _create_api_gateway_from_meta(name, meta):
    """ Create API Gateway with all specified meta.

    :type name: str
    :type meta: dict
    """
    required_parameters = ['resources', 'deploy_stage']
    validate_params(name, meta, required_parameters)

    api_resources = meta['resources']
    deploy_stage = meta['deploy_stage']

    # if _API_GATEWAY_CONN.get_api_by_name(name):
    #     _LOG.info('%s API exists.', name)
    #     return

    api_id = _API_GATEWAY_CONN.create_rest_api(name)['id']
    if api_resources:
        args = []
        for each in api_resources:
            resource_meta = api_resources[each]
            _LOG.info('Creating resource %s ...', each)
            if each.startswith('/'):
                resource_id = _API_GATEWAY_CONN.get_resource_id(api_id, each)
                if resource_id:
                    _LOG.info('Resource %s exists.', each)
                    enable_cors = resource_meta.get('enable_cors')
                    _check_existing_methods(api_id, resource_id, each,
                                            resource_meta, enable_cors)
                else:
                    args.append({
                        'api_id': api_id,
                        'resource_path': each,
                        'resource_meta': resource_meta
                    })
            else:
                raise AssertionError(
                    "API resource must starts with '/', but found %s", each)
        create_pool(_create_resource_from_metadata, 1, args)
    else:
        _LOG.info('There is no resources in %s API Gateway description.', name)
    # add headers
    # waiter b4 customization
    time.sleep(10)
    # TODO move to sdk calls
    _LOG.info('Customizing API Gateway responses...')
    _customize_gateway_responses(api_id)
    # deploy api
    cache_cluster_configuration = meta.get('cluster_cache_configuration')
    root_cache_enabled = cache_cluster_configuration.get(
        'cache_enabled') if cache_cluster_configuration else None
    cache_size = cache_cluster_configuration.get(
        'cache_size') if cache_cluster_configuration else None
    _API_GATEWAY_CONN.deploy_api(api_id, stage_name=deploy_stage,
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
        _API_GATEWAY_CONN.update_configuration(
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
        configure_cache(api_id, deploy_stage, api_resources)
    return describe_api_resources(api_id, meta, name)


def describe_api_resources(name, meta, api_id=None):
    arn = 'arn:aws:apigateway:{0}::/restapis/{1}'.format(CONFIG.region,
                                                         api_id)
    if not api_id:
        api = _API_GATEWAY_CONN.get_api_by_name(name)
        if not api:
            return
        api_id = api['id']

    response = _API_GATEWAY_CONN.get_api(api_id)
    if not response:
        return
    response['resources'] = _API_GATEWAY_CONN.get_resources(api_id)
    _LOG.info('Created %s API Gateway.', name)
    return {
        arn: build_description_obj(response, name, meta)
    }


def _check_existing_methods(api_id, resource_id, resource_path, resource_meta,
                            enable_cors):
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
        if _API_GATEWAY_CONN.get_method(api_id, resource_id, method):
            _LOG.info('Method %s exists.', method)
            continue
        else:
            _LOG.info('Creating method %s for resource %s...',
                      method, resource_id)
            _create_method_from_metadata(api_id, resource_id, resource_path,
                                         method, resource_meta[method],
                                         enable_cors)
    if enable_cors and not _API_GATEWAY_CONN.get_method(api_id, resource_id,
                                                        'OPTIONS'):
        _LOG.info('Enabling CORS for resource %s...', resource_id)
        _API_GATEWAY_CONN.enable_cors_for_resource(api_id, resource_id)


@unpack_kwargs
def _create_resource_from_metadata(api_id, resource_path, resource_meta):
    _API_GATEWAY_CONN.create_resource(api_id, resource_path)
    _LOG.info('Resource %s created.', resource_path)
    resource_id = _API_GATEWAY_CONN.get_resource_id(api_id, resource_path)
    enable_cors = resource_meta.get('enable_cors')
    for method in resource_meta:
        try:
            if method == 'enable_cors' or method not in SUPPORTED_METHODS:
                continue

            method_meta = resource_meta[method]
            _LOG.info('Creating method %s for resource %s...',
                      method, resource_path)
            _create_method_from_metadata(api_id, resource_id, resource_path,
                                         method, method_meta, enable_cors)
        except Exception as e:
            _LOG.error('Resource: {0}, method {1}.'
                       .format(resource_path, method), exc_info=True)
            raise e
        _LOG.info('Method %s for resource %s created.', method, resource_path)
    # create enable cors only after all methods in resource created
    if enable_cors:
        _API_GATEWAY_CONN.enable_cors_for_resource(api_id, resource_id)
        _LOG.info('CORS enabled for resource %s', resource_path)


def _generate_final_response(default_error_pattern=None, responses=None,
                             integration_responses=None):
    if not responses:
        responses = []
    if not integration_responses:
        integration_responses = []
    if default_error_pattern:
        final_responses = [
            each.copy() for each in _DEFAULT_RESPONSES['responses']]
        for resp in responses:
            status_code = resp['status_code']
            is_in_default = False
            for each in final_responses:
                if each['status_code'] == status_code:
                    is_in_default = True
                    each.update(resp)
                    break
            if not is_in_default:
                final_responses.append(resp)

        final_integr_responses = [
            each.copy() for each in
            _DEFAULT_RESPONSES['integration_responses']]
        for resp in integration_responses:
            status_code = resp['status_code']
            is_in_default = False
            for each in final_integr_responses:
                if each['status_code'] == status_code:
                    is_in_default = True
                    each.update(resp)
                    break
            if not is_in_default:
                final_integr_responses.append(resp)
        return final_responses, final_integr_responses
    else:
        return responses, integration_responses


def _create_method_from_metadata(api_id, resource_id, resource_path, method,
                                 method_meta, enable_cors=False):
    resp, integr_resp = _generate_final_response(
        method_meta.get("default_error_pattern"),
        method_meta.get("responses"),
        method_meta.get("integration_responses"))
    # first step: create method
    _API_GATEWAY_CONN.create_method(
        api_id, resource_id, method,
        authorization_type=method_meta.get('authorization_type'),
        authorizer_id=method_meta.get('authorizer_id'),
        api_key_required=method_meta.get('api_key_required'),
        request_parameters=method_meta.get('method_request_parameters'),
        request_models=method_meta.get('method_request_models'))
    # second step: create integration
    integration_type = method_meta.get('integration_type')
    # set up integration - lambda or aws service
    body_template = method_meta.get('integration_request_body_template')
    passthrough_behavior = method_meta.get('integration_passthrough_behavior')
    # TODO split to map - func implementation
    if integration_type:
        if integration_type == 'lambda':
            lambda_name = method_meta['lambda_name']
            # alias has a higher priority than version in arn resolving
            lambda_version = method_meta.get('lambda_version')
            lambda_alias = method_meta.get('lambda_alias')
            lambda_arn = resolve_lambda_arn_by_version_and_alias(lambda_name,
                                                                 lambda_version,
                                                                 lambda_alias)
            enable_proxy = method_meta.get('enable_proxy')
            cache_configuration = method_meta.get('cache_configuration')
            cache_key_parameters = cache_configuration.get(
                'cache_key_parameters') if cache_configuration else None
            _API_GATEWAY_CONN.create_lambda_integration(
                lambda_arn, api_id, resource_id, method, body_template,
                passthrough_behavior, method_meta.get('lambda_region'),
                enable_proxy=enable_proxy,
                cache_key_parameters=cache_key_parameters)
            # add permissions to invoke
            _LAMBDA_CONN.add_invocation_permission(lambda_name,
                                                   "apigateway.amazonaws.com")
        elif integration_type == 'service':
            uri = method_meta.get('uri')
            role = method_meta.get('role')
            integration_method = method_meta.get('integration_method')
            _API_GATEWAY_CONN.create_service_integration(CONFIG.account_id,
                                                         api_id,
                                                         resource_id, method,
                                                         integration_method,
                                                         role, uri,
                                                         body_template,
                                                         passthrough_behavior)
        elif integration_type == 'mock':
            _API_GATEWAY_CONN.create_mock_integration(api_id, resource_id,
                                                      method,
                                                      body_template,
                                                      passthrough_behavior)
        elif integration_type == 'http':
            integration_method = method_meta.get('integration_method')
            uri = method_meta.get('uri')
            enable_proxy = method_meta.get('enable_proxy')
            _API_GATEWAY_CONN.create_http_integration(api_id, resource_id,
                                                      method,
                                                      integration_method, uri,
                                                      body_template,
                                                      passthrough_behavior,
                                                      enable_proxy)
        else:
            raise AssertionError('%s integration type does not exist.',
                                 integration_type)
    # third step: setup method responses
    if resp:
        for response in resp:
            _API_GATEWAY_CONN.create_method_response(
                api_id, resource_id, method, response.get('status_code'),
                response.get('response_parameters'),
                response.get('response_models'), enable_cors)
    else:
        _API_GATEWAY_CONN.create_method_response(
            api_id, resource_id, method, enable_cors=enable_cors)
    # fourth step: setup integration responses
    if integr_resp:
        for each in integr_resp:
            _API_GATEWAY_CONN.create_integration_response(
                api_id, resource_id, method, each.get('status_code'),
                each.get('error_regex'),
                each.get('response_parameters'),
                each.get('response_templates'), enable_cors)
    else:
        _API_GATEWAY_CONN.create_integration_response(
            api_id, resource_id, method, enable_cors=enable_cors)


def _customize_gateway_responses(api_id):
    responses = _API_GATEWAY_CONN.describe_responses(api_id)
    response_types = [r['responseType'] for r in responses]
    for response_type in response_types:
        time.sleep(10)
        _API_GATEWAY_CONN.add_header_for_response(api_id, response_type,
                                                  _CORS_HEADER_NAME,
                                                  _CORS_HEADER_VALUE)


def remove_api_gateways(args):
    for arg in args:
        _remove_api_gateway(**arg)
        # wait for success deletion
        time.sleep(60)


def _remove_api_gateway(arn, config):
    api_id = config['description']['id']
    try:
        _API_GATEWAY_CONN.remove_api(api_id)
        _LOG.info('API Gateway %s was removed.', api_id)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            _LOG.warn('API Gateway %s is not found', api_id)
        else:
            raise e
