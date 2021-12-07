import json

from syndicate.core.constants import RESOURCES_FILE_NAME
from pathlib import Path
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)
from syndicate.commons.log_helper import get_logger, get_user_logger

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.base_generator')
USER_LOG = get_user_logger()


class BaseDeploymentResourceGenerator:
    RESOURCE_TYPE = None

    def __init__(self, **kwargs):
        self.resource_name = kwargs.get('resource_name')
        self.project_path = kwargs.get('project_path')

        if not self.RESOURCE_TYPE:
            message = f"RESOURCE_TYPE variable inside class " \
                      f"'{type(self).__name__}' must be specified"
            _LOG.error(message)
            raise AssertionError(message)

    def generate_deployment_resource(self) -> dict:
        """Generates resource meta for current object and returns it"""
        USER_LOG.info(f"Generating deployment resources for "
                      f"{self.RESOURCE_TYPE} '{self.resource_name}'")
        return {
            self.resource_name: self._generate_resource_configuration()
        }

    def _generate_resource_configuration(self) -> dict:
        """Return the dict with just resource configuration"""
        _LOG.info("Generating configuration for "
                  f"{self.RESOURCE_TYPE} '{self.resource_name}'")
        return {
            "resource_type": self.RESOURCE_TYPE
        }

    def write_deployment_resource(self):
        resources_path = Path(self.project_path, RESOURCES_FILE_NAME)
        deployment_resources = json.loads(_read_content_from_file(
            resources_path
        ))
        deployment_resources.update(self.generate_deployment_resource())
        USER_LOG.info("Writing deployment resources for "
                      f"{self.RESOURCE_TYPE} '{self.resource_name}' "
                      f"to the file")
        _write_content_to_file(resources_path,
                               json.dumps(deployment_resources, indent=2))
