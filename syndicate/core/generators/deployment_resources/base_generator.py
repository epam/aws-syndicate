import json

from syndicate.core.constants import RESOURCES_FILE_NAME
from pathlib import Path
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)

class BaseDeploymentResourceGenerator:
    RESOURCE_TYPE = None

    def __init__(self, **kwargs):
        self.resource_name = kwargs.get('resource_name')
        self.project_path = kwargs.get('project_path')

        if not self.RESOURCE_TYPE:
            raise AssertionError(f"RESOURCE_TYPE variable inside class "
                                 f"'{type(self).__name__}' must be specified")

    def generate_deployment_resource(self) -> dict:
        """Generates resource meta for current object and returns it"""
        return {
            self.resource_name: self._generate_resource_configuration()
        }

    def _generate_resource_configuration(self) -> dict:
        """Return the dict with just resource configuration"""
        return {
            "resource_type": self.RESOURCE_TYPE
        }

    def write_deployment_resource(self):
        resources_path = Path(self.project_path, RESOURCES_FILE_NAME)
        deployment_resources = json.loads(_read_content_from_file(
            resources_path
        ))
        deployment_resources.update(self.generate_deployment_resource())
        _write_content_to_file(resources_path,
                               json.dumps(deployment_resources, indent=2))