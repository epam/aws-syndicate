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
    REQUIRED_RAPAMS = ['deploy_stage', ]
    NOT_REQUIRED_DEFAULTS = {
        'dependencies': list,
        'resources': dict,
        'minimum_compression_size': None
    }


class ApiGatewayResourceGenerator(BaseConfigurationGenerator):
    NOT_REQUIRED_DEFAULTS = {
        'enable_cors': bool
    }

    def __init__(self, **kwargs):
        self.resource_path = kwargs.pop('path')
        self.api_gateway_name = kwargs.pop('api_name')
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

        deployment_resources = None
        path_with_api = None
        for path in reversed(paths_with_api):
            deployment_resources = json.loads(_read_content_from_file(path))
            path_with_api = path
            if self.resource_path in \
                    deployment_resources[self.api_gateway_name]['resources']:
                message = f"Resource '{self.resource_path}' was found in " \
                          f"api gateway '{self.api_gateway_name}' in file " \
                          f"'{path}'"
                _LOG.warning(f"Found duplicate while generating meta. "
                             f"{message}")
                if click.confirm(f"{message} Overwrite?"):
                    break
                else:
                    USER_LOG.warning(
                        f"Skipping resource '{self.resource_path}'")
                    return

        USER_LOG.warning(
            f"Overwriting API gateway resource '{self.resource_path}'")
        deployment_resources[self.api_gateway_name]['resources'][
            self.resource_path] = self.generate_whole_configuration()
        _write_content_to_file(path_with_api,
                               json.dumps(deployment_resources, indent=2))
