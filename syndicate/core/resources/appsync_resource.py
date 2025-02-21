import io
import os.path
import posixpath
import shutil
import time
from pathlib import PurePath
from zipfile import ZipFile

from botocore.exceptions import ClientError

from syndicate.exceptions import ArtifactError, \
    ResourceProcessingError, ResourceNotFoundError, ParameterError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import ARTIFACTS_FOLDER
from syndicate.core.helper import build_path, unpack_kwargs, \
    dict_keys_to_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params, \
    build_description_obj

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

API_REQUIRED_PARAMS = ['schema_path']
DATA_SOURCE_REQUIRED_PARAMS = ['name', 'type']
RESOLVER_REQUIRED_PARAMS = ['type_name', 'field_name', 'runtime']
RESOLVER_DEFAULT_KIND = 'UNIT'

DEFAULT_FUNC_VTL_VERSION = '2018-05-29'
FUNCTION_REQUIRED_PARAMS = ['runtime', 'data_source_name']

AWS_REGION_PARAMETER = 'aws_region'
AWS_LAMBDA_TYPE = 'AWS_LAMBDA'
AWS_CUP_TYPE = 'AMAZON_COGNITO_USER_POOLS'

DATA_SOURCE_TYPE_CONFIG_MAPPING = {
    AWS_LAMBDA_TYPE: 'lambda_config',
    'AMAZON_DYNAMODB': 'dynamodb_config',
    'AMAZON_ELASTICSEARCH': 'elasticsearch_config',
    'HTTP': 'http_config',
    'RELATIONAL_DATABASE': 'relational_database_config',
    'AMAZON_OPENSEARCH_SERVICE': 'open_search_service_config',
    'AMAZON_EVENTBRIDGE': 'event_bridge_config'
}

ONE_DAY_IN_SECONDS = 86400


class AppSyncResource(BaseResource):

    def __init__(self, appsync_conn, s3_conn, cup_conn, cw_logs_conn,
                 deploy_target_bucket, deploy_target_bucket_key_compound,
                 account_id) -> None:
        from syndicate.core import CONF_PATH
        self.appsync_conn = appsync_conn
        self.s3_conn = s3_conn
        self.cup_conn = cup_conn
        self.cw_logs_conn = cw_logs_conn
        self.conf_path = CONF_PATH
        self.deploy_target_bucket_key_compound = \
            deploy_target_bucket_key_compound
        self.deploy_target_bucket = deploy_target_bucket
        self.account_id = account_id

    def create_graphql_api(self, args):
        """ Create GraphQL API in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_graphql_api_from_meta, args, 1)

    @unpack_kwargs
    def _create_graphql_api_from_meta(self, name, meta):
        """ Create GraphQL API from meta description.

        :type name: str
        :type meta: dict
        """
        extract_to = None
        validate_params(name, meta, API_REQUIRED_PARAMS)

        api = self.appsync_conn.get_graphql_api_by_name(name)
        if api:
            _LOG.warning(f'AppSync API {name} already exists.')
            return self.describe_graphql_api(
                name=name, meta=meta, api_id=api['apiId'])

        archive_path = meta.get('deployment_package')
        if archive_path:
            extract_to = self._extract_zip(archive_path, name)
        auth_type = meta.get('primary_auth_type')
        extra_auth_types = meta.get('extra_auth_types', [])
        lambda_auth_config = meta.get('lambda_authorizer_config', {})
        user_pool_config = meta.get('user_pool_config', {})

        if auth_type == AWS_LAMBDA_TYPE:
            lambda_region = lambda_auth_config.pop(AWS_REGION_PARAMETER, None)
            lambda_name = lambda_auth_config.pop('resource_name', None)
            if not lambda_region or not lambda_name:
                lambda_auth_config = {}
                USER_LOG.error(
                    f"Authorization type '{auth_type}' can't be configured "
                    f"for AppSync '{name}' because lambda resource name or "
                    f"aws region is not specified")
            else:
                lambda_arn = self.build_lambda_arn(
                    region=lambda_region,
                    name=lambda_name)
                lambda_auth_config['authorizer_uri'] = lambda_arn

        if auth_type == AWS_CUP_TYPE:
            cup_name = user_pool_config.pop('resource_name', None)
            cup_id = self.cup_conn.if_pool_exists_by_name(cup_name)
            if cup_id:
                user_pool_config['user_pool_id'] = cup_id
            else:
                user_pool_config = {}
                USER_LOG.error(
                    f"Authorization type '{auth_type}' can't be configured "
                    f"for AppSync '{name}' because Cognito User Pool "
                    f"{cup_name} not found")

        updated_extra_auth_types, is_extra_auth_api_key = \
            self._process_extra_auth(extra_auth_types, name)

        api_id = self.appsync_conn.create_graphql_api(
            name, auth_type=auth_type, tags=meta.get('tags'),
            user_pool_config=user_pool_config,
            open_id_config=meta.get('open_id_config'),
            lambda_auth_config=lambda_auth_config,
            log_config=self._resolve_log_config(
                meta.get('log_config', {}), name
            ),
            xray_enabled=meta.get('xray_enabled'),
            extra_auth_types=updated_extra_auth_types)

        if auth_type == 'API_KEY' or is_extra_auth_api_key:
            api_key_expiration = meta.get('api_key_expiration_days', 7)
            now = time.time()
            api_key_expires = \
                int(now + api_key_expiration * ONE_DAY_IN_SECONDS)
            self.appsync_conn.create_api_key(api_id, expires=api_key_expires)

        if schema_path := meta.get('schema_path'):
            schema_full_path = build_path(extract_to, schema_path)
            if not extract_to or not os.path.exists(schema_full_path):
                raise ArtifactError(
                    f'\'{schema_full_path}\' file not found for '
                    f'AppSync \'{name}\''
                )

            with open(schema_full_path, 'r', encoding='utf-8') as file:
                schema_definition = file.read()

            status, details = \
                self.appsync_conn.create_schema(api_id, schema_definition)
            if status != 'SUCCESS':
                error_message = (
                    f"An error occurred when creating schema. "
                    f"Operation status: '{status}'. ")
                if details:
                    error_message += f"Details: '{details}'"
                raise ResourceProcessingError(error_message)
            else:
                _LOG.info(
                    f"Schema of the AppSync '{name}' created successfully")

        data_sources_meta = meta.get('data_sources', [])
        for data_source_meta in data_sources_meta:
            params = self._build_data_source_params_from_meta(data_source_meta)
            if not params:
                continue
            self.appsync_conn.create_data_source(api_id, **params)

        functions_config = []
        functions_meta = meta.get('functions', [])
        for func_meta in functions_meta:
            params = self._build_function_params_from_meta(
                func_meta, extract_to)
            if not params:
                continue
            func_config = self.appsync_conn.create_function(api_id, params)
            functions_config.append(func_config)

        resolvers_meta = meta.get('resolvers', [])
        for resolver_meta in resolvers_meta:
            params = self._build_resolver_params_from_meta(
                resolver_meta, extract_to, functions_config)
            if not params:
                continue
            self.appsync_conn.create_resolver(api_id, **params)

        if extract_to:
            shutil.rmtree(extract_to, ignore_errors=True)
        _LOG.info(f'Created AppSync GraphQL API {api_id}')
        return self.describe_graphql_api(name=name, meta=meta, api_id=api_id)

    def _build_data_source_params_from_meta(self, source_meta: dict):
        source_name = source_meta.get('name')
        try:
            validate_params(
                source_name, source_meta, DATA_SOURCE_REQUIRED_PARAMS)
        except ParameterError as e:
            _LOG.warning(str(e))
            _LOG.warning(f'Skipping data source \'{source_name}\'...')
            return

        _LOG.info(f'Altering data source \'{source_name}\'...')
        source_config = None
        source_type = source_meta.get('type')

        data_source_params = {
            'name': source_name,
            'source_type': source_type
        }

        if source_description := source_meta.get('description'):
            data_source_params['description'] = source_description

        if role_name := source_meta.get('service_role_name'):
            role_arn = self._build_iam_role_arn(role_name)
            data_source_params['service_role_arn'] = role_arn

        if config_key := DATA_SOURCE_TYPE_CONFIG_MAPPING.get(source_type):
            source_config = source_meta.get(config_key)

        if source_type == AWS_LAMBDA_TYPE and source_config:
            region = source_config.pop(AWS_REGION_PARAMETER, None)
            lambda_name = source_config.pop('lambda_name', None)
            source_config['lambda_function_arn'] = self.build_lambda_arn(
                lambda_name, region)
        elif source_type == 'AMAZON_EVENTBRIDGE' and source_config:
            region = source_config.pop(AWS_REGION_PARAMETER)
            event_bus = source_config.pop('event_bus_name')
            source_config['event_bus_arn'] = self.build_event_bus_arn(
                event_bus, region)

        if source_config:
            data_source_params['source_config'] = source_config

        return data_source_params

    def build_lambda_arn(self, name, region):
        arn = f'arn:aws:lambda:{region}:{self.account_id}:function:{name}'
        return arn

    def build_event_bus_arn(self, name, region):
        arn = f'arn:aws:events:{region}:{self.account_id}:event-bus/{name}'
        return arn

    def _build_iam_role_arn(self, name):
        return f'arn:aws:iam::{self.account_id}:role/{name}'

    @staticmethod
    def _build_resolver_params_from_meta(resolver_meta, artifacts_path,
                                         existing_functions=None):
        existing_functions = existing_functions or []
        type_name = resolver_meta.get('type_name')
        field_name = resolver_meta.get('field_name')
        try:
            validate_params(type_name + ':' + field_name, resolver_meta,
                            RESOLVER_REQUIRED_PARAMS)
        except ParameterError as e:
            _LOG.warning(str(e))
            _LOG.warning(f'Skipping resolver for type \'{type_name}\' '
                         f'and field \'{field_name}\'...')
            return

        _LOG.info(f'Altering resolver for type \'{type_name}\' and field '
                  f'\'{field_name}\'...')
        resolver_params = {
            'type_name': type_name,
            'field_name': field_name,
        }
        kind = resolver_meta.get('kind', RESOLVER_DEFAULT_KIND)
        resolver_params['kind'] = kind
        if kind == RESOLVER_DEFAULT_KIND:
            resolver_params['data_source_name'] = \
                resolver_meta['data_source_name']
        elif kind == 'PIPELINE':
            _LOG.info("Trying to resolve functions IDs")
            function_names = \
                resolver_meta.get('pipeline_config', {}).get('functions', [])
            function_ids = []
            for func_name in function_names:
                func_id = None
                for func_info in existing_functions:
                    if func_name == func_info['name']:
                        func_id = func_info['functionId']
                        function_ids.append(func_id)
                        _LOG.debug(
                            f"Successfully resolved ID '{func_id}' for the "
                            f"function '{func_name}'")
                        break
                if not func_id:
                    _LOG.warning(f"ID for the function '{func_name}' was "
                                 f"not resolved")

            resolver_params['pipeline_config'] = {
                'functions': function_ids
            }

        if resolver_meta.get('runtime') in ('JS', 'APPSYNC_JS'):
            runtime = {
                'name': 'APPSYNC_JS',
                'runtimeVersion': '1.0.0'
            }
            resolver_params['runtime'] = runtime
        else:
            runtime = None

        if runtime:
            code_path = build_path(artifacts_path,
                                   resolver_meta.get('code_path'))
            if not artifacts_path or not os.path.exists(code_path):
                raise ArtifactError(
                    f"Resolver code file for type '{type_name}' and field "
                    f"'{field_name}' not found.")

            with open(code_path, 'r', encoding='utf-8') as file:
                code = file.read()
            resolver_params['code'] = code
        else:
            _LOG.debug('Runtime is not JS')
            request_template_path = build_path(
                artifacts_path,
                resolver_meta.get('request_mapping_template_path'))
            if not artifacts_path or not os.path.exists(request_template_path):
                raise ArtifactError(
                    f"Resolver request mapping template file for type "
                    f"'{type_name}' and field '{field_name}' not found.")
            else:
                with open(request_template_path, 'r',
                          encoding='utf-8') as file:
                    request_mapping_template = file.read()

            response_template_path = build_path(
                artifacts_path,
                resolver_meta.get('response_mapping_template_path'))
            if not artifacts_path or not os.path.exists(response_template_path):
                raise ArtifactError(
                    f"Resolver response mapping template file for type "
                    f"'{type_name}' and field '{field_name}' not found.")
            else:
                with open(response_template_path, 'r',
                          encoding='utf-8') as file:
                    response_mapping_template = file.read()

            resolver_params['request_mapping_template'] = \
                request_mapping_template
            resolver_params['response_mapping_template'] = \
                response_mapping_template

        if max_batch_size := resolver_meta.get('max_batch_size'):
            resolver_params['max_batch_size'] = max_batch_size

        return resolver_params

    @staticmethod
    def _build_function_params_from_meta(func_meta, artifacts_path):
        func_name = func_meta['name']
        _LOG.debug(f"Building parameters for the function '{func_name}'")
        try:
            validate_params(func_name, func_meta, FUNCTION_REQUIRED_PARAMS)
        except ParameterError as e:
            _LOG.warning(str(e))
            _LOG.warning(f"Skipping function '{func_name}'...")
            return

        function_params = {
            'name': func_name,
            'data_source_name': func_meta['data_source_name']
        }

        if description := func_meta.get('description'):
            function_params['description'] = description

        if func_meta.get('runtime') in ('JS', 'APPSYNC_JS'):
            runtime = {
                'name': 'APPSYNC_JS',
                'runtimeVersion': '1.0.0'
            }
            function_params['runtime'] = runtime
        else:
            runtime = None

        if runtime:
            code_path = build_path(artifacts_path,
                                   func_meta.get('code_path'))
            if not artifacts_path or not os.path.exists(code_path):
                raise ArtifactError(
                    f"Function '{func_name}' code file not found.")

            with open(code_path, 'r', encoding='utf-8') as file:
                code = file.read()
            function_params['code'] = code
        else:
            _LOG.debug('Runtime is not JS')
            function_params['function_version'] = \
                func_meta.get('function_version', DEFAULT_FUNC_VTL_VERSION)
            request_template_path = build_path(
                artifacts_path,
                func_meta.get('request_mapping_template_path'))
            if not artifacts_path or not os.path.exists(request_template_path):
                raise ArtifactError(
                    f"Function '{func_name}' request mapping template file "
                    f"not found.")
            else:
                with open(request_template_path, 'r',
                          encoding='utf-8') as file:
                    request_mapping_template = file.read()

            response_template_path = build_path(
                artifacts_path,
                func_meta.get('response_mapping_template_path'))
            if not artifacts_path or not os.path.exists(response_template_path):
                raise ArtifactError(
                    f"Function '{func_name}' response mapping template file "
                    f"not found.")
            else:
                with open(response_template_path, 'r',
                          encoding='utf-8') as file:
                    response_mapping_template = file.read()

            function_params['request_mapping_template'] = \
                request_mapping_template
            function_params['response_mapping_template'] = \
                response_mapping_template

        if max_batch_size := func_meta.get('max_batch_size'):
            function_params['max_batch_size'] = max_batch_size

        return function_params

    def _resolve_log_config(self, log_config: dict, api_name: str) -> dict:
        if log_config.pop('logging_enabled', False):
            _LOG.debug(
                f"Building log_config parameters for the AppSync '{api_name}'"
            )
            log_role_name = log_config.pop('cloud_watch_logs_role_name', None)
            if log_role_name:
                log_config['cloud_watch_logs_role_arn'] = \
                    self._build_iam_role_arn(log_role_name)
            else:
                _LOG.warning(
                    f"Cloud watch logs can't be configured for the AppSync "
                    f"'{api_name}' because 'cloud_watch_logs_role_name' not "
                    f"specified"
                )
                log_config = {}
        else:
            log_config = {}
        return log_config

    def build_graphql_api_arn(self, api_id: str) -> str:
        return f'arn:aws:appsync:{self.appsync_conn.client.meta.region_name}' \
               f':{self.account_id}:apis/{api_id}'

    def describe_graphql_api(self, name, meta, api_id=None):
        if not api_id:
            api = self.appsync_conn.get_graphql_api_by_name(name)
            if not api:
                return {}
            api_id = api['apiId']

        response = {'apiId': api_id}

        arn = self.build_graphql_api_arn(api_id)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def remove_graphql_api(self, args):
        return self.create_pool(self._remove_graphql_api, args)

    @unpack_kwargs
    def _remove_graphql_api(self, arn, config):
        api_id = config['description']['apiId']
        try:
            self.appsync_conn.delete_graphql_api(api_id)
            group_names = self.cw_logs_conn.get_log_group_names()
            for each in group_names:
                if api_id == each.split('/')[-1]:
                    self.cw_logs_conn.delete_log_group_name(each)
            _LOG.info(f'GraphQL API {api_id} was removed.')
            return {arn: config}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                _LOG.warning(f'GraphQL API {api_id} is not found')
                return {arn: config}
            else:
                raise e

    def update_graphql_api(self, args):
        return self.create_pool(self._update_graphql_api, args, 1)

    @unpack_kwargs
    def _update_graphql_api(self, name, meta, context):
        extract_to = None
        api = self.appsync_conn.get_graphql_api_by_name(name)
        if not api:
            raise ResourceNotFoundError(f'{name} GraphQL API does not exist.')

        archive_path = meta.get('deployment_package')
        if archive_path:
            extract_to = self._extract_zip(archive_path, name)
        else:
            _LOG.warning('Cannot find appsync deployment package!')
        api_id = api['apiId']
        auth_type = meta.get('primary_auth_type')
        extra_auth_types = meta.get('extra_auth_types', [])
        lambda_auth_config = meta.get('lambda_authorizer_config', {})
        user_pool_config = meta.get('user_pool_config', {})

        if auth_type == AWS_LAMBDA_TYPE:
            lambda_region = lambda_auth_config.pop(AWS_REGION_PARAMETER, None)
            lambda_name = lambda_auth_config.pop('resource_name', None)
            if not lambda_region or not lambda_name:
                lambda_auth_config = {}
                USER_LOG.error(
                    f"Authorization type '{auth_type}' can't be configured "
                    f"for AppSync '{name}' because lambda resource name or "
                    f"aws region is not specified")
            else:
                lambda_arn = self.build_lambda_arn(
                    region=lambda_region,
                    name=lambda_name)
                lambda_auth_config['authorizer_uri'] = lambda_arn

        if auth_type == AWS_CUP_TYPE:
            cup_name = user_pool_config.pop('resource_name', None)
            cup_id = self.cup_conn.if_pool_exists_by_name(cup_name)
            if cup_id:
                user_pool_config['user_pool_id'] = cup_id
            else:
                user_pool_config = {}
                USER_LOG.error(
                    f"Authorization type '{auth_type}' can't be configured "
                    f"for AppSync '{name}' because Cognito User Pool "
                    f"{cup_name} not found")

        updated_extra_auth_types, is_extra_auth_api_key = \
            self._process_extra_auth(extra_auth_types, name)

        self.appsync_conn.update_graphql_api(
            api_id, name, auth_type=auth_type,
            user_pool_config=user_pool_config,
            open_id_config=meta.get('open_id_config'),
            lambda_auth_config=lambda_auth_config,
            log_config=self._resolve_log_config(
                meta.get('log_config', {}), name
            ),
            xray_enabled=meta.get('xray_enabled'),
            extra_auth_types=updated_extra_auth_types)

        if auth_type == 'API_KEY' or is_extra_auth_api_key:
            if not self.get_active_api_keys(api_id):
                api_key_expiration = meta.get('api_key_expiration_days', 7)
                now = time.time()
                api_key_expires = \
                    int(now + api_key_expiration * ONE_DAY_IN_SECONDS)
                self.appsync_conn.create_api_key(
                    api_id, expires=api_key_expires)

        if schema_path := meta.get('schema_path'):
            schema_full_path = build_path(extract_to, schema_path)
            if not extract_to or not os.path.exists(schema_full_path):
                raise ArtifactError(
                    f'\'{schema_full_path}\' file not found for '
                    f'AppSync \'{name}\'')

            with open(schema_full_path, 'r', encoding='utf-8') as file:
                schema_definition = file.read()

            status, details = \
                self.appsync_conn.create_schema(api_id, schema_definition)
            if status != 'SUCCESS':
                error_message = (
                    f"An error occurred when updating schema. "
                    f"Operation status: '{status}'. ")
                if details:
                    error_message += f"Details: '{details}'"
                raise ResourceProcessingError(error_message)
            else:
                _LOG.info(
                    f"Schema of the AppSync '{name}' updated successfully")

        existent_sources = self.appsync_conn.list_data_sources(api_id)
        data_sources_meta = meta.get('data_sources', [])
        for source_meta in data_sources_meta:
            to_create = True
            for source in existent_sources:
                if source['name'] == source_meta['name']:
                    # update an existent one
                    to_create = False
                    params = self._build_data_source_params_from_meta(
                        source_meta)
                    if not params:
                        break
                    _LOG.debug(f"Updating data source '{source['name']}'")
                    self.appsync_conn.update_data_source(api_id, **params)
                    existent_sources.remove(source)
                    break

            # create a new one
            if to_create:
                params = self._build_data_source_params_from_meta(source_meta)
                if not params:
                    continue
                _LOG.debug(f"Creating data source '{source_meta['name']}'")
                self.appsync_conn.create_data_source(api_id, **params)

        for source in existent_sources:
            self.appsync_conn.delete_data_source(api_id, source['name'])

        actual_funcs = []
        existent_funcs = self.appsync_conn.list_functions(api_id)
        funcs_meta = meta.get('functions', [])
        for func_meta in funcs_meta:
            to_create = True
            for func_conf in existent_funcs:
                if func_meta['name'] == func_conf['name']:
                    # update an existent one
                    to_create = False
                    params = self._build_function_params_from_meta(
                        func_meta, extract_to
                    )
                    if not params:
                        break
                    _LOG.debug(f"Updating function '{func_conf['name']}'")
                    actual_funcs.append(
                        self.appsync_conn.update_function(
                            api_id, func_conf['functionId'], params))
                    existent_funcs.remove(func_conf)
                    break
            # create a new one
            if to_create:
                params = self._build_function_params_from_meta(
                    func_meta, extract_to
                )
                if not params:
                    break
                _LOG.debug(f"Creating function '{func_meta['name']}'")
                actual_funcs.append(
                    self.appsync_conn.create_function(api_id, params))

        types = self.appsync_conn.list_types(api_id)
        existent_resolvers = []
        for t in types:
            existent_resolvers.extend(
                self.appsync_conn.list_resolvers(api_id, t['name']))
        resolvers_meta = meta.get('resolvers', [])

        for resolver_meta in resolvers_meta:
            to_create = True
            for resolver in existent_resolvers:
                if resolver['typeName'] == resolver_meta['type_name'] and \
                        resolver['fieldName'] == resolver_meta['field_name']:
                    # update an existent one
                    to_create = False
                    params = self._build_resolver_params_from_meta(
                            resolver_meta, extract_to, actual_funcs)
                    if not params:
                        break
                    _LOG.debug(
                        f"Updating resolver for type '{resolver['typeName']}' "
                        f"and field '{resolver['fieldName']}'")
                    self.appsync_conn.update_resolver(api_id, **params)
                    existent_resolvers.remove(resolver)
                    break

            # create a new one
            if to_create:
                params = self._build_resolver_params_from_meta(
                            resolver_meta, extract_to, actual_funcs)
                if not params:
                    continue
                _LOG.debug(
                    f"Creating resolver for type '{resolver_meta['typeName']}' "
                    f"and field '{resolver_meta['fieldName']}'")
                self.appsync_conn.create_resolver(api_id, **params)

        for resolver in existent_resolvers:
            self.appsync_conn.delete_resolver(api_id,
                                              type_name=resolver['typeName'],
                                              field_name=resolver['fieldName'])

        for func_conf in existent_funcs:
            self.appsync_conn.delete_function(api_id, func_conf['functionId'])

        _LOG.info(f'Updated AppSync GraphQL API {api_id}')
        return self.describe_graphql_api(name=name, meta=meta, api_id=api_id)

    def _extract_zip(self, path: str, name: str):
        from syndicate.core import PROJECT_STATE

        extract_to = PurePath(self.conf_path, ARTIFACTS_FOLDER,
                              name).as_posix()
        artifact_src_path = posixpath.join(
            self.deploy_target_bucket_key_compound,
            PROJECT_STATE.current_bundle, path)

        if not self.s3_conn.is_file_exists(self.deploy_target_bucket,
                                           artifact_src_path):
            raise ArtifactError(
                f"Deployment package for Appsync '{name}' not found by the "
                f"path '{artifact_src_path}'")

        _LOG.info(f'Downloading an artifact for Appsync \'{name}\'')
        with io.BytesIO() as artifact:
            self.s3_conn.download_to_file(
                    bucket_name=self.deploy_target_bucket,
                    key=artifact_src_path,
                    file=artifact)
            with ZipFile(artifact, 'r') as zf:
                zf.extractall(extract_to)
        return extract_to

    def _process_extra_auth(self, extra_auth_types, api_name):
        is_extra_auth_api_key = False
        result = []
        for auth in extra_auth_types:
            if auth['authentication_type'] == AWS_LAMBDA_TYPE:
                lambda_region = \
                    auth.get('lambda_authorizer_config', {}).pop(
                        AWS_REGION_PARAMETER, None)
                lambda_name = \
                    auth.get('lambda_authorizer_config', {}).pop(
                        'resource_name', None)
                if not lambda_region or not lambda_name:
                    USER_LOG.error(
                        f"Authorization type '{AWS_LAMBDA_TYPE}' can't be "
                        f"configured for AppSync '{api_name}' because lambda "
                        f"resource name or aws region is not specified")
                else:
                    lambda_arn = self.build_lambda_arn(
                        region=lambda_region,
                        name=lambda_name)
                    auth['lambda_authorizer_config']['authorizer_uri'] = \
                        lambda_arn
                    result.append(dict_keys_to_camel_case(auth))
            elif auth['authentication_type'] == AWS_CUP_TYPE:
                cup_name = \
                    auth.get('user_pool_config', {}).pop(
                        'resource_name', None)
                cup_id = self.cup_conn.if_pool_exists_by_name(cup_name)
                if not cup_id:
                    USER_LOG.error(
                        f"Authorization type '{AWS_CUP_TYPE}' can't be "
                        f"configured for AppSync '{api_name}' because Cognito "
                        f"User Pool '{cup_name}' not found")
                else:
                    auth['user_pool_config']['user_pool_id'] = cup_id
                    result.append(dict_keys_to_camel_case(auth))
            elif auth['authentication_type'] == 'API_KEY':
                result.append(dict_keys_to_camel_case(auth))
                is_extra_auth_api_key = True
            else:
                result.append(dict_keys_to_camel_case(auth))

        return result, is_extra_auth_api_key

    def get_active_api_keys(self, api_id):
        api_keys = self.appsync_conn.list_api_keys(api_id)
        now = time.time()
        return [api_key for api_key in api_keys if api_key['expires'] > now]
