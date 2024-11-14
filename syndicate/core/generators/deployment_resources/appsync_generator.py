import json
from pathlib import Path, PurePath

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import APPSYNC_TYPE, DYNAMO_TABLE_TYPE, IAM_ROLE
from syndicate.core.generators import _write_content_to_file
from syndicate.core.generators.deployment_resources import \
    BaseConfigurationGenerator
from click import confirm as click_confirm


_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class AppSyncConfigurationGenerator(BaseConfigurationGenerator):
    """Contains common method for AppSync meta generators"""

    def __init__(self, **kwargs):
        self.appsync_name = kwargs.pop('appsync_name')
        super().__init__(**kwargs)


class AppSyncDataSourceGenerator(AppSyncConfigurationGenerator):
    CONFIGURATION = {
        'name': str,
        'description': None,
        'type': None,
        'resource_name': None,
        'region': None,
        'service_role_name': None,
        'lambda_config': None,
        'dynamodb_config': None
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write(self):
        paths_with_appsync = self._get_resource_meta_paths(self.appsync_name,
                                                           APPSYNC_TYPE)
        error_message = None
        if not paths_with_appsync:
            error_message = f"AppSync api '{self.appsync_name}' was not found"
        elif len(paths_with_appsync) > 1:
            error_message = (
                f"AppSync API '{self.appsync_name}' was found in several "
                f"deployment resource files. Duplication of resources is "
                f"forbidden.")

        if error_message:
            _LOG.error(error_message)
            raise ValueError(error_message)

        path_to_dr = paths_with_appsync[0]
        deployment_resources = self._get_deployment_resources_file_content(
            path_to_dr)

        data_sources = \
            deployment_resources[self.appsync_name].get('data_sources', [])
        current_ds_name = self._dict.get('name')
        for data_source in data_sources:
            if current_ds_name == data_source['name']:
                message = (f"Data source with the name '{current_ds_name}' "
                           f"already exists.")
                if click_confirm(f"{message} Overwrite?"):
                    _LOG.warning(
                        f"Overwriting data source '{current_ds_name}'")
                    data_sources.remove(data_source)
                else:
                    _LOG.warning(
                        f"Skipping data source '{current_ds_name}'")
                    raise RuntimeError
        data_sources.append(self._resolve_configuration())
        deployment_resources[self.appsync_name]['data_sources'] = data_sources
        _write_content_to_file(path_to_dr,
                               json.dumps(deployment_resources, indent=2))

    def _resolve_configuration(self, defaults_dict=None):
        from syndicate.core import CONFIG
        region = self._dict.pop('region', None) or CONFIG.region
        data_source_type = self._dict.get('type')
        if data_source_type != 'NONE':
            self._validate_resource_existence(
                self._dict.get('service_role_name'),
                IAM_ROLE)
        match data_source_type:
            case 'AWS_LAMBDA':
                lambda_name = self._dict.pop('resource_name')
                self._validate_lambda_existence(lambda_name)
                self._dict['lambda_config'] = {
                    'lambda_name': lambda_name,
                    'aws_region': region
                }
            case 'AMAZON_DYNAMODB':
                table_name = self._dict.pop('resource_name')
                self._validate_resource_existence(table_name,
                                                  DYNAMO_TABLE_TYPE)
                self._dict['dynamodb_config'] = {
                    'table_name': table_name,
                    'aws_region': region
                }

        return super()._resolve_configuration()


class AppSyncResolverGenerator(AppSyncConfigurationGenerator):
    CONFIGURATION = {
        'type_name': str,
        'field_name': str,
        'data_source_name': str,
        'runtime': str,
        'code_path': None,
        'request_mapping_template_path': None,
        'response_mapping_template_path': None,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write(self):
        paths_with_appsync = self._get_resource_meta_paths(self.appsync_name,
                                                           APPSYNC_TYPE)
        error_message = None
        if not paths_with_appsync:
            error_message = f"AppSync api '{self.appsync_name}' was not found"
        elif len(paths_with_appsync) > 1:
            error_message = (
                f"AppSync API '{self.appsync_name}' was found in several "
                f"deployment resource files. Duplication of resources is "
                f"forbidden.")

        if error_message:
            _LOG.error(error_message)
            raise ValueError(error_message)

        path_to_dr = paths_with_appsync[0]
        deployment_resources = self._get_deployment_resources_file_content(
            path_to_dr)

        data_sources = \
            deployment_resources[self.appsync_name].get('data_sources', [])
        current_ds_name = self._dict.get('data_source_name')
        error_message = (
            f"Data source '{current_ds_name}' not found in the SyncApp "
            f"'{self.appsync_name}' definition.")
        for data_source in data_sources:
            if current_ds_name == data_source['name']:
                error_message = None
                break
        if error_message:
            raise ValueError(error_message)

        resolvers = \
            deployment_resources[self.appsync_name].get('resolvers', [])
        current_type_name = self._dict.get('type_name')
        current_field_name = self._dict.get('field_name')
        for resolver in resolvers:
            if (resolver['type_name'] == current_type_name and
                    resolver['field_name'] == current_field_name):
                message = (f"The resolver for the type '{current_type_name}' "
                           f"and field '{current_field_name}' already exists.")
                if click_confirm(f"{message} Overwrite?"):
                    _LOG.warning(
                        f"Overwriting resolver for the type '{current_ds_name}' "
                        f" and field '{current_field_name}'")
                    resolvers.remove(resolver)
                else:
                    _LOG.warning(
                        f"Skipping data source '{current_ds_name}'")
                    raise RuntimeError

        resolvers.append(self._resolve_configuration())
        deployment_resources[self.appsync_name]['resolvers'] = resolvers
        _write_content_to_file(path_to_dr,
                               json.dumps(deployment_resources, indent=2))

    def _resolve_configuration(self, defaults_dict=None):
        from syndicate.core import CONFIG
        self._dict['request_mapping_template_path'] = \
            self._dict.pop('req_mapping_template', None)
        self._dict['response_mapping_template_path'] = \
            self._dict.pop('resp_mapping_template', None)
        path_to_project = CONFIG.project_path
        runtime = self._dict.get('runtime')
        paths_to_check = []
        if runtime == 'JS':
            paths_to_check.append(self._dict.get('code_path'))
        if runtime == 'VTL':
            paths_to_check.append(
                self._dict.get('request_mapping_template_path'))
            paths_to_check.append(
                self._dict.get('response_mapping_template_path'))

        for path_to_file in paths_to_check:
            abs_path_to_file = path_to_file
            if not Path(path_to_file).is_absolute():
                abs_path_to_file = \
                    PurePath(path_to_project, path_to_file).as_posix()
                _LOG.info(f"Path to file '{path_to_file}' resolved as "
                          f"'{abs_path_to_file}'")
            if not Path(abs_path_to_file).is_file():
                raise ValueError(f"File '{abs_path_to_file}' not found")

        return super()._resolve_configuration()
