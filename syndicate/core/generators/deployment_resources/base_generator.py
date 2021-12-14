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


class BaseConfigurationGenerator:
    """The params below are required to be specified in each heir.
    'REQUIRED' and 'NOT_REQUIRED' mean to be required or not required for user
    input. But it doesn't necessarily mean that they are required or not
    required for 'syndicate deploy' comamnd"""
    REQUIRED_RAPAMS: list = []
    NOT_REQUIRED_DEFAULTS: dict = {}

    def __init__(self, **kwargs):
        self._dict = dict(kwargs)
        self.project_path = self._dict.pop('project_path')

    def _resolve_required_configuration(self) -> dict:
        """Returns a dict with just required params values"""
        result = {name: self._dict.get(name) for name in self.REQUIRED_RAPAMS}
        _LOG.info(f"Resolved required params: {result}")
        return result

    def _resolve_not_required_configuration(self, defaults_dict=None) -> dict:
        """Return a dict with not required params and sets default values if
        another one wasn't given"""
        defaults_dict = defaults_dict or self.NOT_REQUIRED_DEFAULTS
        _LOG.info(f"Resolving not required params...")
        result = {}
        for param_name, default_value in defaults_dict.items():
            given_value = self._dict.get(param_name)
            if not given_value:
                if isinstance(default_value, type):
                    to_assign = default_value()
                    _LOG.info(f"Setting default value - the object "
                              f"'{to_assign}' of the class '{default_value}' "
                              f"for param '{param_name}'")
                    result[param_name] = default_value()
                elif isinstance(default_value, dict):
                    result[param_name] = \
                        self._resolve_not_required_configuration(
                            defaults_dict=default_value)
                elif default_value:
                    _LOG.info(f"Setting default value '{default_value}' "
                              f"for param '{param_name}'")
                    result[param_name] = default_value
            else:
                _LOG.info(f"Setting given value '{given_value}' for "
                          f"param '{param_name}'")
                result[param_name] = given_value
        return result

    def generate_whole_configuration(self):
        """Generates the whole configuration for the entity"""
        result = self._resolve_required_configuration()
        result.update(self._resolve_not_required_configuration())
        return result

    def _get_deployment_resources_files(self) -> list:
        """Returns the list of paths to each deployment_resources.json file"""
        _LOG.info(f"Recursively getting all the deployment_resources.json with"
                  f" root '{self.project_path}'")
        dep_res_files = glob.glob(str(Path(self.project_path, "**",
                                           RESOURCES_FILE_NAME)),
                                  recursive=True)
        return dep_res_files

    def _find_resources_by_type(self, resources_type) -> dict:
        """Returns the dict, where key is a path to deployment_resources file
        and value is a set of entities' names with given resource_type"""
        dep_res_files = self._get_deployment_resources_files()
        resources = {}
        _LOG.info(f"Looking for resource '{resources_type}' in meta")
        for file in dep_res_files:
            data = json.loads(_read_content_from_file(file))
            resources[file] = set(filter(
                lambda name: data[name]['resource_type'] == resources_type,
                data))
        _LOG.info(f"Found '{resources}' inside with type '{resources_type}'")
        return resources

    def _get_resource_meta_paths(self, resource_name, resource_type):
        """Returns the list of paths to deployment resouces file, where the
        resouces with given name and type is declared. (In case of api gw you
        possibly may have two declarations of the same api in different files
        """
        available_resources = self._find_resources_by_type(resource_type)
        paths = []
        _LOG.info(f"Looking for {resource_type} '{resource_name}' in meta...")
        for path, resources in available_resources.items():
            if resource_name in resources:
                _LOG.info(f"Found '{resource_name}' in meta from '{path}'")
                paths.append(path)
        _LOG.info(f"Found {resource_type} '{resource_name}' in "
                  f"these files: '{paths}'")
        return paths

    def write(self):
        """The main method to write resouces"""
        raise NotImplementedError()


class BaseDeploymentResourceGenerator(BaseConfigurationGenerator):
    RESOURCE_TYPE: str = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.resource_name = self._dict.pop('resource_name')

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
        """Return a dict with just resource configuration"""
        _LOG.info("Generating configuration for "
                  f"{self.RESOURCE_TYPE} '{self.resource_name}'")
        result = {
            "resource_type": self.RESOURCE_TYPE,
        }
        result.update(self.generate_whole_configuration())
        return result

    def write(self):
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
                raise RuntimeError

        deployment_resources = json.loads(_read_content_from_file(
            resources_file
        ))
        deployment_resources.update(self.generate_deployment_resource())
        USER_LOG.info(f"Writing deployment resources for "
                      f"{self.RESOURCE_TYPE} '{self.resource_name}' "
                      f"to the file '{resources_file}'")
        _write_content_to_file(resources_file,
                               json.dumps(deployment_resources, indent=2))

    def _find_file_with_duplicate(self):
        """Looks for self.resouce_name inside each deployment_resource.json.
        If a duplicate is found, returns the path to file with it."""
        paths = self._get_resource_meta_paths(self.resource_name,
                                              self.RESOURCE_TYPE)
        if paths:
            _LOG.warning(f"Duplicated {self.RESOURCE_TYPE} with name "
                         f"'{self.resource_name}' was found in: {paths}")
            return paths[0]
        _LOG.info(f"No duplicated {self.RESOURCE_TYPE} with "
                  f"name '{self.resource_name}' was found")
