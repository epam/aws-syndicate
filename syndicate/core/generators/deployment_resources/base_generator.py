import glob
import json
from pathlib import Path

import click
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import RESOURCES_FILE_NAME, API_GATEWAY_TYPE
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.base_generator')
USER_LOG = get_user_logger()


class BaseDeploymentResourceGenerator:
    RESOURCE_TYPE = None

    def __init__(self, **kwargs):
        self.project_path = kwargs.get('project_path')
        self.resource_name = kwargs.get('resource_name')

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

    def write_deployment_resource(self) -> bool:
        """Writes generated meta to root deployment_resources. If resource
        with the name {self.resource_name} already exists, it'll ask a
        user whether overwrite it or not. If 'yes', resource meta will
        be written to the file, where the duplicate was found"""

        resources_file = Path(self.project_path, RESOURCES_FILE_NAME)
        duplicated_file = self._find_file_with_duplicate()
        if duplicated_file:
            message = f"Resource with name '{self.resource_name}' " \
                      f"was found in file '{duplicated_file}'."
            _LOG.warning(f"Found duplicate while generating meta. {message}")
            if click.confirm(f"{message} Overwrite?"):
                USER_LOG.warning(f"Overwriting resource '{self.resource_name}'")
                resources_file = duplicated_file
            else:
                USER_LOG.warning(f"Skipping resource '{self.resource_name}'")
                return False

        deployment_resources = json.loads(_read_content_from_file(
            resources_file
        ))
        deployment_resources.update(self.generate_deployment_resource())
        USER_LOG.info(f"Writing deployment resources for "
                      f"{self.RESOURCE_TYPE} '{self.resource_name}' "
                      f"to the file '{resources_file}'")
        _write_content_to_file(resources_file,
                               json.dumps(deployment_resources, indent=2))
        return True


    def _find_file_with_duplicate(self):
        """Looks for self.resouce_name inside each deployment_resource.json.
        If a duplicate is found, returns the path to file with it. If the
        duplicate and the current generator are API_GATEWAYs, the file
        will be skipped because two API_GATEWAY resources can be merged"""
        dep_res_files = glob.glob(str(Path(self.project_path, "**",
                                           RESOURCES_FILE_NAME)),
                                  recursive=True)
        for file in dep_res_files:
            _LOG.info(f'Looking for duplicates iside {file}')
            data = json.loads(_read_content_from_file(file))
            if self.resource_name in data:
                if not self.RESOURCE_TYPE == data[self.resource_name][
                    'resource_type'] == API_GATEWAY_TYPE:
                    _LOG.warning(f"Duplicate '{data[self.resource_name]}' "
                                 f"inside {file} was found. Returning...")
                    return file
