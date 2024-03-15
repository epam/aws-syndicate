import glob
import json
import re
from pathlib import Path

import click
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import RESOURCES_FILE_NAME
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.base_generator')
USER_LOG = get_user_logger()


class BaseConfigurationGenerator:
    """Contains params and their values for the current entity:
    - if the value of param is None, the param will be set only if it's
      given. If it isn't given, will be omitted;
    - if the value of param is set, will be used as default in case user
      doesn't put it;
    - if the value is type (dict, list, bool), the value will be the object
      of the type;
    - if the value is a dict, it will be handled and resolved resursively.
    """
    CONFIGURATION: dict = {}

    def __init__(self, **kwargs):
        self._dict = dict(kwargs)
        self.project_path = self._dict.pop('project_path')

    def _resolve_configuration(self, defaults_dict=None) -> dict:
        """Returns a dict with resolved params for current entity based on
        given params"""
        defaults_dict = defaults_dict or self.CONFIGURATION
        _LOG.info(f"Resolving not required params...")
        result = {}
        for param_name, default_value in defaults_dict.items():
            given_value = self._dict.get(param_name)
            if given_value == None or given_value == ():  # click's nulls
                if isinstance(default_value, type):
                    to_assign = default_value()
                    _LOG.info(f"Setting default value - the object "
                              f"'{to_assign}' of the class '{default_value}' "
                              f"for param '{param_name}'")
                    result[param_name] = to_assign
                elif isinstance(default_value, dict):
                    result[param_name] = \
                        self._resolve_configuration(
                            defaults_dict=default_value)
                elif default_value != None:
                    _LOG.info(f"Setting default value '{default_value}' "
                              f"for param '{param_name}'")
                    result[param_name] = default_value
            else:
                _LOG.info(f"Setting given value '{given_value}' for "
                          f"param '{param_name}'")
                if isinstance(given_value, tuple):
                    result[param_name] = list(given_value)
                else:
                    result[param_name] = given_value
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

    @staticmethod
    def _validate_lambda_existence(lambda_name):
        from syndicate.core import PROJECT_STATE
        _LOG.info(f"Validating existence of lambda: {lambda_name}")

        if lambda_name not in PROJECT_STATE.lambdas:
            message = f"Lambda '{lambda_name}' wasn't found"
            _LOG.error(f"Validation error: {message}")
            raise ValueError(message)
        _LOG.info(f"Validation successfully finished, lambda exists")

    def write(self):
        """The main method to write resouces"""
        raise NotImplementedError()


class BaseDeploymentResourceGenerator(BaseConfigurationGenerator):
    RESOURCE_TYPE: str = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.resource_name = self._dict.pop('resource_name').strip()
        self._validate_resource_name()

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
        result.update(self._resolve_configuration())
        return result

    def write(self):
        """Writes generated meta to the highest, level-wise,
        deployment_resources, excluding the lambdas sub-folder. If resource
        with the name {self.resource_name} already exists, it'll ask a
        user whether overwrite it or not. If 'yes', resource meta will
        be written to the file, where the duplicate was found"""

        resources_file = next(
            iter(path for path in Path(self.project_path).rglob(
                RESOURCES_FILE_NAME) if 'lambdas' not in path.parts),
            Path(self.project_path, RESOURCES_FILE_NAME)
        )

        if not resources_file.exists():
            USER_LOG.warning('Root "deployment_resources.json" wasn\'t found. '
                             'Creating the one...')
            _write_content_to_file(resources_file, json.dumps({}))
        duplicated_file = self._find_file_with_duplicate()
        if duplicated_file:
            message = f"Resource with name '{self.resource_name}' " \
                      f"was found in file '{duplicated_file}'."
            _LOG.warning(f"Found duplicate while generating meta. {message}")
            if click.confirm(f"{message} Overwrite?"):
                USER_LOG.warning(
                    f"Overwriting resource '{self.resource_name}'")
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

    def _validate_resource_name(self):
        """Validates self.resource_name"""
        to_validate: str = self.resource_name
        _LOG.info(f"Validating resource name: '{to_validate}'")
        error = None

        invalid_character = re.search("[^a-zA-Z0-9._-]", to_validate)
        if not 3 <= len(to_validate) <= 64:
            error = "resource name length must be between 3 and 64 characters"
        elif invalid_character:
            error = f"resource name cannot contain: " \
                    f"'{invalid_character.group()}'"
        elif any(to_validate.startswith(prefix) for prefix in '_.-'):
            error = "resource name cannot start with any of these: '_', '.', '-'"
        elif any(to_validate.endswith(suffix) for suffix in '_.-'):
            error = "resource name cannot end with any of these: '_', '.', '-'"
        if error:
            _LOG.error(f"Resource name validation error: {error}")
            raise click.BadParameter(error, param_hint="resource_name")
        _LOG.info(f"Resource name: '{to_validate}' passed the validation")
