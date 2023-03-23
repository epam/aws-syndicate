import json

import click

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import API_GATEWAY_TYPE
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator, BaseConfigurationGenerator

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.api_gateway_generator')
USER_LOG = get_user_logger()


class ApiGatewayGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = API_GATEWAY_TYPE
    CONFIGURATION = {
        'deploy_stage': None,
        'dependencies': list,
        'resources': dict,
        'minimum_compression_size': None
    }


class ApiGatewayConfigurationGenerator(BaseConfigurationGenerator):
    """Contains common method for resource and method generators"""

    def __init__(self, **kwargs):
        self.api_gateway_name = kwargs.pop('api_name')
        super().__init__(**kwargs)

    def get_meta_with_resource(self, paths_with_api: list, resource_path: str):
        """Returns the path to deployment resources with api which contains
        resource with given path"""
        for path in paths_with_api:
            deployment_resources = json.loads(_read_content_from_file(path))
            if resource_path in deployment_resources[self.api_gateway_name][
                'resources']:
                _LOG.info(f"Found resource '{resource_path}' in api "
                          f"'{self.api_gateway_name}' in file '{path}'")
                return path, deployment_resources


class ApiGatewayResourceGenerator(ApiGatewayConfigurationGenerator):
    CONFIGURATION = {
        'enable_cors': bool
    }

    def __init__(self, **kwargs):
        self.resource_path = kwargs.pop('path')
        super().__init__(**kwargs)

    def write(self):
        """Adds resource to API gateway"""
        paths_with_api = self._get_resource_meta_paths(self.api_gateway_name,
                                                       API_GATEWAY_TYPE)
        if not paths_with_api:
            message = f"Api gateway '{self.api_gateway_name}' was not found"
            _LOG.error(message)
            raise ValueError(message)
        USER_LOG.info(f"Adding resource '{self.resource_path}' to api "
                      f"'{self.api_gateway_name}'...")

        path_with_resources = self.get_meta_with_resource(paths_with_api,
                                                          self.resource_path)
        if not path_with_resources:
            path_with_api = paths_with_api[0]
            deployment_resources = json.loads(
                _read_content_from_file(path_with_api))
        else:
            path_with_api, deployment_resources = path_with_resources
            message = f"Resource '{self.resource_path}' was found in " \
                      f"api gateway '{self.api_gateway_name}' in file " \
                      f"'{path_with_api}'"
            _LOG.warning(f"Found duplicate while generating meta. "
                         f"{message}")
            if not click.confirm(f"{message} Overwrite?"):
                USER_LOG.warning(f"Skipping resource "
                                 f"'{self.resource_path}'")
                raise RuntimeError

        USER_LOG.info(f"Adding resource '{self.resource_path}' to api "
                      f"'{self.api_gateway_name}'...")
        deployment_resources[self.api_gateway_name]['resources'][
            self.resource_path] = self._resolve_configuration()
        _write_content_to_file(path_with_api,
                               json.dumps(deployment_resources, indent=2))


class ApiGatewayResourceMethodGenerator(ApiGatewayConfigurationGenerator):
    CONFIGURATION = {
        'authorization_type': "NONE",
        'integration_type': 'mock',
        'lambda_name': None,
        'lamdba_region': None,
        'api_key_required': bool,
        'method_request_parameters': dict,
        'integration_request_body_template': dict,
        'responses': list,
        'integration_responses': list,
        'default_error_pattern': True,
    }

    def __init__(self, **kwargs):
        self.resource_path = kwargs.pop('path')
        self.method = kwargs.pop('method')
        super().__init__(**kwargs)

    def write(self):
        paths_with_api = self._get_resource_meta_paths(self.api_gateway_name,
                                                       API_GATEWAY_TYPE)
        if not paths_with_api:
            message = f"Api gateway '{self.api_gateway_name}' was not found"
            _LOG.error(message)
            raise ValueError(message)

        path_with_resources = self.get_meta_with_resource(paths_with_api,
                                                          self.resource_path)
        if not path_with_resources:
            message = f"Resouce '{self.resource_path}' wasn't found in api " \
                      f"'{self.api_gateway_name}'"
            _LOG.error(message)
            raise ValueError(message)

        path_with_api, deployment_resources = path_with_resources

        if self.method in deployment_resources[self.api_gateway_name][
            'resources'][self.resource_path]:
            message = f"Method '{self.method}' was found in resource " \
                      f"'{self.resource_path}' from gateway " \
                      f"'{self.api_gateway_name}' in file '{path_with_api}'"
            _LOG.warning(f"Found duplicate while generating meta. "
                         f"{message}")
            if not click.confirm(f"{message} Overwrite?"):
                USER_LOG.warning(f"Skipping resource "
                                 f"'{self.resource_path}'")
                raise RuntimeError

        USER_LOG.info(f"Adding method '{self.method}' to resource "
                      f"'{self.resource_path}' to api "
                      f"'{self.api_gateway_name}'...")

        deployment_resources[self.api_gateway_name]['resources'][
            self.resource_path][self.method] = \
            self._resolve_configuration()
        _write_content_to_file(path_with_api,
                               json.dumps(deployment_resources, indent=2))

    def _resolve_configuration(self, defaults_dict=None):
        if self._dict.get('integration_type') == 'lambda':
            self.validate_integration_lambda_existence()
        else:
            if 'lamdba_name' in self._dict:
                self._dict.pop('lambda_name')
        return super()._resolve_configuration()

    def validate_integration_lambda_existence(self):
        from syndicate.core import PROJECT_STATE
        lambda_name = self._dict.get('lambda_name')
        _LOG.info(f"Validating existence of lambda: {lambda_name}")

        if not lambda_name in PROJECT_STATE.lambdas:
            message = f"Lambda '{lambda_name}' wasn't found"
            _LOG.error(f"Validation error: {message}")
            raise ValueError(message)
        _LOG.info(f"Validation successfully finished, lambda exists")
