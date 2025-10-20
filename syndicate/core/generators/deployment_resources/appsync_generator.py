import json
from pathlib import Path, PurePath

from syndicate.exceptions import ResourceMetadataError, AbortedError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import DYNAMO_TABLE_TYPE, IAM_ROLE, \
    COGNITO_USER_POOL_TYPE, APPSYNC_CONFIG_FILE_NAME, \
    APPSYNC_JS_RESOLVER_CODE_DEFAULT_FILE_NAME, \
    APPSYNC_VTL_RESOLVER_REQ_MT_DEFAULT_FILE_NAME, \
    APPSYNC_VTL_RESOLVER_RESP_MT_DEFAULT_FILE_NAME, APPSYNC_SRC_FOLDER, \
    DEFAULT_JSON_INDENT
from syndicate.core.generators import _write_content_to_file, \
    _read_content_from_file, _mkdir, _touch
from syndicate.core.generators.contents import \
    _generate_syncapp_js_resolver_code, _generate_syncapp_vtl_resolver_req_mt, \
    _generate_syncapp_vtl_resolver_resp_mt
from syndicate.core.generators.deployment_resources import \
    BaseConfigurationGenerator
from click import confirm as click_confirm


APPSYNC_RESOLVERS_DIR = 'resolvers'
APPSYNC_FUNCTIONS_DIR = 'functions'
DEFAULT_FUNC_VTL_RMT_VERSION = '2018-05-29'

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class AppSyncConfigurationGenerator(BaseConfigurationGenerator):
    """Contains common method for AppSync meta generators"""

    def __init__(self, **kwargs):
        from syndicate.core import CONFIG
        path_to_project = CONFIG.project_path
        self.appsync_name = kwargs.pop('api_name')
        self.appsync_path = PurePath(path_to_project, APPSYNC_SRC_FOLDER,
                                     self.appsync_name).as_posix()
        self.appsync_config = self._get_appsync_config()
        self.region = CONFIG.region
        super().__init__(**kwargs)

    def _get_appsync_config(self):
        path_to_config = PurePath(self.appsync_path,
                                  APPSYNC_CONFIG_FILE_NAME).as_posix()
        if not Path(path_to_config).is_file():
            raise ResourceMetadataError(
                f"Config file of the AppSync '{self.appsync_name}' not found. "
                f"Please make sure that the AppSync exists.")
        return json.loads(_read_content_from_file(path_to_config))

    def _save_config(self):
        _write_content_to_file(
            PurePath(self.appsync_path, APPSYNC_CONFIG_FILE_NAME).as_posix(),
            json.dumps(self.appsync_config, indent=DEFAULT_JSON_INDENT))


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
        data_sources = self.appsync_config.get('data_sources', [])
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
                    raise AbortedError
        data_sources.append(self._resolve_configuration())
        self.appsync_config['data_sources'] = data_sources
        self._save_config()

    def _resolve_configuration(self, defaults_dict=None):
        region = self._dict.pop('region', None) or self.region
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


class AppSyncFunctionGenerator(AppSyncConfigurationGenerator):
    CONFIGURATION = {
        'name': str,
        'description': str,
        'data_source_name': str,
        'runtime': str,
        'code_path': None,
        'function_version': None,
        'request_mapping_template_path': None,
        'response_mapping_template_path': None,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write(self):
        data_sources = self.appsync_config.get('data_sources', [])
        current_ds_name = self._dict.get('data_source_name')
        error_message = (
            f"Data source '{current_ds_name}' not found in the SyncApp "
            f"'{self.appsync_name}' definition.")
        for data_source in data_sources:
            if current_ds_name == data_source['name']:
                self._dict['data_source_type'] = data_source['type']
                error_message = None
                break
        if error_message:
            raise ResourceMetadataError(error_message)

        current_func_name = self._dict['name']
        functions = self.appsync_config.get('functions', [])
        for function in functions:
            if function['name'].lower() == current_func_name.lower():
                message = (f"The function with the name '{current_func_name}' "
                           f"already exists.")
                if click_confirm(f"{message} Overwrite?"):
                    _LOG.warning(
                        f"Overwriting function '{current_func_name}'")
                    functions.remove(function)
                else:
                    _LOG.warning(f"Skipping function'{current_func_name}'")
                    raise AbortedError

        functions.append(self._resolve_configuration())
        self.appsync_config['functions'] = functions
        self._save_config()

    def _resolve_configuration(self, defaults_dict=None):
        runtime = self._dict.get('runtime')
        internal_path_to_func = PurePath(
            APPSYNC_FUNCTIONS_DIR,
            self._dict.get('name').lower()).as_posix()

        path_to_func = PurePath(
            self.appsync_path,
            internal_path_to_func).as_posix()

        paths_to_code = PurePath(
            path_to_func,
            APPSYNC_JS_RESOLVER_CODE_DEFAULT_FILE_NAME).as_posix()

        paths_to_req_mapping_template = PurePath(
            path_to_func,
            APPSYNC_VTL_RESOLVER_REQ_MT_DEFAULT_FILE_NAME).as_posix()
        paths_to_resp_mapping_template = PurePath(
            path_to_func,
            APPSYNC_VTL_RESOLVER_RESP_MT_DEFAULT_FILE_NAME).as_posix()

        if not Path(path_to_func).exists():
            _mkdir(path_to_func)
        if runtime == 'JS':
            Path(paths_to_req_mapping_template).unlink(missing_ok=True)
            Path(paths_to_resp_mapping_template).unlink(missing_ok=True)
            self._dict['code_path'] = PurePath(
                internal_path_to_func,
                APPSYNC_JS_RESOLVER_CODE_DEFAULT_FILE_NAME).as_posix()
            code_content = _generate_syncapp_js_resolver_code()
            _touch(paths_to_code)
            _write_content_to_file(paths_to_code, code_content)
        if runtime == 'VTL':
            Path(paths_to_code).unlink(missing_ok=True)
            req_mapping_template = _generate_syncapp_vtl_resolver_req_mt(
                self._dict['data_source_type'])
            resp_mapping_template = _generate_syncapp_vtl_resolver_resp_mt(
                self._dict['data_source_type'])

            self._dict['function_version'] = DEFAULT_FUNC_VTL_RMT_VERSION
            self._dict['request_mapping_template_path'] = PurePath(
                internal_path_to_func,
                APPSYNC_VTL_RESOLVER_REQ_MT_DEFAULT_FILE_NAME).as_posix()
            self._dict['response_mapping_template_path'] = PurePath(
                internal_path_to_func,
                APPSYNC_VTL_RESOLVER_RESP_MT_DEFAULT_FILE_NAME).as_posix()

            _touch(paths_to_req_mapping_template)
            _write_content_to_file(paths_to_req_mapping_template,
                                   req_mapping_template)

            _touch(paths_to_resp_mapping_template)
            _write_content_to_file(paths_to_resp_mapping_template,
                                   resp_mapping_template)

        return super()._resolve_configuration()


class AppSyncResolverGenerator(AppSyncConfigurationGenerator):
    CONFIGURATION = {
        'kind': str,
        'type_name': str,
        'field_name': str,
        'data_source_name': None,
        'runtime': str,
        'pipeline_config': None,
        'code_path': None,
        'request_mapping_template_path': None,
        'response_mapping_template_path': None,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write(self):
        if self._dict['kind'] == 'UNIT':
            data_sources = self.appsync_config.get('data_sources', [])
            current_ds_name = self._dict.get('data_source_name')
            error_message = (
                f"Data source '{current_ds_name}' not found in the SyncApp "
                f"'{self.appsync_name}' definition.")
            for data_source in data_sources:
                if current_ds_name == data_source['name']:
                    self._dict['data_source_type'] = data_source['type']
                    error_message = None
                    break
            if error_message:
                raise ResourceMetadataError(error_message)
        elif self._dict['kind'] == 'PIPELINE':
            if (functions := self.appsync_config.get('functions', [])) is None:
                functions = []
            if (curr_functions := self._dict.get('function_name', [])) is None:
                curr_functions = []
            absent_funcs = []

            for func_name in set(curr_functions):
                func_exist = False
                for func_conf in functions:
                    if func_conf['name'].lower() == func_name.lower():
                        func_exist = True
                        break
                if not func_exist:
                    absent_funcs.append(func_name)
            if absent_funcs:
                raise ResourceMetadataError(
                    f"The next function/s '{absent_funcs}' not found in the "
                    f"SyncApp '{self.appsync_name}' definition.")
            self._dict['pipeline_config'] = {
                'functions': curr_functions
            }
        resolvers = self.appsync_config.get('resolvers', [])
        current_type_name = self._dict.get('type_name')
        current_field_name = self._dict.get('field_name')
        for resolver in resolvers:
            if (resolver['type_name'].lower() == current_type_name.lower()
                    and
               resolver['field_name'].lower() == current_field_name.lower()):
                message = (f"The resolver for the type '{current_type_name}' "
                           f"and field '{current_field_name}' already exists.")
                if click_confirm(f"{message} Overwrite?"):
                    _LOG.warning(
                        f"Overwriting resolver for the type "
                        f"'{current_type_name}' and field "
                        f"'{current_field_name}'")
                    resolvers.remove(resolver)
                else:
                    _LOG.warning(
                        f"Skipping resolver for the type "
                        f"'{current_type_name}' and field "
                        f"'{current_field_name}'")
                    raise AbortedError

        resolvers.append(self._resolve_configuration())
        self.appsync_config['resolvers'] = resolvers
        self._save_config()

    def _resolve_configuration(self, defaults_dict=None):
        runtime = self._dict.get('runtime')
        internal_path_to_field = PurePath(
            APPSYNC_RESOLVERS_DIR, self._dict.get('type_name').lower(),
            self._dict.get('field_name').lower()).as_posix()

        path_to_field = PurePath(
            self.appsync_path,
            internal_path_to_field).as_posix()

        paths_to_code = PurePath(
            path_to_field,
            APPSYNC_JS_RESOLVER_CODE_DEFAULT_FILE_NAME).as_posix()

        paths_to_req_mapping_template = PurePath(
            path_to_field,
            APPSYNC_VTL_RESOLVER_REQ_MT_DEFAULT_FILE_NAME).as_posix()
        paths_to_resp_mapping_template = PurePath(
            path_to_field,
            APPSYNC_VTL_RESOLVER_RESP_MT_DEFAULT_FILE_NAME).as_posix()

        if not Path(path_to_field).exists():
            _mkdir(path_to_field)
        if runtime == 'JS':
            Path(paths_to_req_mapping_template).unlink(missing_ok=True)
            Path(paths_to_resp_mapping_template).unlink(missing_ok=True)
            self._dict['code_path'] = PurePath(
                internal_path_to_field,
                APPSYNC_JS_RESOLVER_CODE_DEFAULT_FILE_NAME).as_posix()
            code_content = _generate_syncapp_js_resolver_code()
            _touch(paths_to_code)
            _write_content_to_file(paths_to_code, code_content)
        if runtime == 'VTL':
            Path(paths_to_code).unlink(missing_ok=True)
            data_source_type = (
                self._dict['data_source_type']
                if self._dict['kind'] == 'UNIT' else 'PIPELINE')
            req_mapping_template = _generate_syncapp_vtl_resolver_req_mt(
                data_source_type)
            resp_mapping_template = _generate_syncapp_vtl_resolver_resp_mt(
                data_source_type)

            self._dict['request_mapping_template_path'] = PurePath(
                internal_path_to_field,
                APPSYNC_VTL_RESOLVER_REQ_MT_DEFAULT_FILE_NAME).as_posix()
            self._dict['response_mapping_template_path'] = PurePath(
                internal_path_to_field,
                APPSYNC_VTL_RESOLVER_RESP_MT_DEFAULT_FILE_NAME).as_posix()

            _touch(paths_to_req_mapping_template)
            _write_content_to_file(paths_to_req_mapping_template,
                                   req_mapping_template)

            _touch(paths_to_resp_mapping_template)
            _write_content_to_file(paths_to_resp_mapping_template,
                                   resp_mapping_template)

        return super()._resolve_configuration()


class AppSyncAuthorizationGenerator(AppSyncConfigurationGenerator):
    CONFIGURATION = {
        'primary_auth_type': None,
        'extra_auth_types': None,
        'lambda_authorizer_config': None,
        'user_pool_config': None,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def write(self):
        primary_auth = self.appsync_config.get('primary_auth_type')
        self._dict['current_primary_auth'] = primary_auth
        if self._dict['type'] == 'primary':
            if primary_auth:
                message = "Primary authorization already exists."
                if click_confirm(f"{message} Overwrite?"):
                    _LOG.warning(f"Overwriting primary authorization")
                    self.appsync_config.pop('lambda_authorizer_config', None)
                    self.appsync_config.pop('user_pool_config', None)
                else:
                    _LOG.warning(f"Skipping primary authorization creation")
                    raise AbortedError

        extra_auth = self.appsync_config.get('extra_auth_types', [])
        self._dict['current_extra_auth'] = extra_auth
        if self._dict['type'] == 'extra':
            if not primary_auth:
                raise ResourceMetadataError(
                    'Primary authorization is mandatory, please configure it '
                    'first'
                )
            new_extra_auth_type = self._dict['auth_type']
            for auth_type in extra_auth:
                if auth_type['authentication_type'] == new_extra_auth_type:
                    message = (f"Extra authorization '{new_extra_auth_type}' "
                               f"already exists.")
                    if click_confirm(f"{message} Overwrite?"):
                        _LOG.warning(f"Overwriting extra authorization")
                    else:
                        _LOG.warning(
                            f"Skipping extra authorization creation")
                        raise AbortedError

        self.appsync_config.update(self._resolve_configuration())
        self._save_config()

    def _resolve_configuration(self, defaults_dict=None):
        authorizer_type = self._dict.pop('type')
        authentication_type = self._dict.pop('auth_type')
        authentication_config = self._resolve_authentication_configuration(
            authentication_type
        )
        if authorizer_type == 'primary':
            primary_auth_type = authentication_config['authentication_type']
            lambda_config = \
                authentication_config.get('lambda_authorizer_config')
            cognito_config = authentication_config.get('user_pool_config')

            for extra_auth in self._dict['current_extra_auth']:
                if primary_auth_type == extra_auth['authentication_type']:
                    raise ResourceMetadataError(
                        f"'{primary_auth_type}' can't be configured as "
                        f" the primary authorization because it is already "
                        f"configured as an extra authorization provider")

            self._dict['primary_auth_type'] = primary_auth_type
            if lambda_config:
                self._dict['lambda_authorizer_config'] = lambda_config
            if cognito_config:
                cognito_config['default_action'] = 'DENY'
                self._dict['user_pool_config'] = cognito_config
        elif authorizer_type == 'extra':
            new_auth_type = authentication_config['authentication_type']

            if new_auth_type == self._dict['current_primary_auth']:
                raise ResourceMetadataError(
                    f"'{new_auth_type}' can't be configured as "
                    f"an extra authorization provider because it is already "
                    f"configured as the primary authorization")

            current_extra_auth = self._dict.pop('current_extra_auth', [])
            for extra_auth in current_extra_auth:
                if extra_auth['authentication_type'] == new_auth_type:
                    current_extra_auth.remove(extra_auth)

            current_extra_auth.append(authentication_config)
            self._dict['extra_auth_types'] = current_extra_auth

        return super()._resolve_configuration()

    def _resolve_authentication_configuration(self, auth_type: str) -> dict:
        region = self._dict.pop('region', None) or self.region

        match auth_type:
            case 'API_KEY':
                return {'authentication_type': 'API_KEY'}
            case 'AWS_IAM':
                return {'authentication_type': 'AWS_IAM'}
            case 'AWS_LAMBDA':
                lambda_name = self._dict.pop('resource_name')
                self._validate_lambda_existence(lambda_name)

                return {
                    'authentication_type': 'AWS_LAMBDA',
                    'lambda_authorizer_config': {
                        'authorizer_result_ttl_in_seconds': 300,
                        'resource_name': lambda_name,
                        'aws_region': region
                    }
                }
            case 'AMAZON_COGNITO_USER_POOLS':
                cup_name = self._dict.pop('resource_name')
                self._validate_resource_existence(cup_name,
                                                  COGNITO_USER_POOL_TYPE)

                return {
                    'authentication_type': 'AMAZON_COGNITO_USER_POOLS',
                    'user_pool_config': {
                        'resource_name': cup_name,
                        'aws_region': region
                    }
                }
