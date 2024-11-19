import io
import os.path
import posixpath
import shutil
from pathlib import PurePath
from zipfile import ZipFile

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.constants import ARTIFACTS_FOLDER
from syndicate.core.helper import build_path, unpack_kwargs, \
    dict_keys_to_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params, \
    build_description_obj

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')

API_REQUIRED_PARAMS = ['schema_path']
DATA_SOURCE_REQUIRED_PARAMS = ['name', 'type']
RESOLVER_REQUIRED_PARAMS = ['type_name', 'field_name', 'runtime',
                            'data_source_name']
RESOLVER_DEFAULT_KIND = 'UNIT'

DATA_SOURCE_TYPE_CONFIG_MAPPING = {
    'AWS_LAMBDA': 'lambda_config',
    'AMAZON_DYNAMODB': 'dynamodb_config',
    'AMAZON_ELASTICSEARCH': 'elasticsearch_config',
    'HTTP': 'http_config',
    'RELATIONAL_DATABASE': 'relational_database_config',
    'AMAZON_OPENSEARCH_SERVICE': 'open_search_service_config',
    'AMAZON_EVENTBRIDGE': 'event_bridge_config'
}


class AppSyncResource(BaseResource):

    def __init__(self, appsync_conn, s3_conn, deploy_target_bucket,
                 deploy_target_bucket_key_compound, account_id) -> None:
        from syndicate.core import CONF_PATH
        self.appsync_conn = appsync_conn
        self.s3_conn = s3_conn
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
        validate_params(name, meta, API_REQUIRED_PARAMS)

        api = self.appsync_conn.get_graphql_api_by_name(name)
        if api:
            _LOG.warning(f'AppSync API {name} already exists.')
            return self.describe_graphql_api(
                name=name, meta=meta, api_id=api['apiId'])

        archive_path = meta['deployment_package']
        extract_to = self._extract_zip(archive_path, name)
        auth_type = meta.get('primary_auth_type')
        extra_auth_types = meta.get('extra_auth_types', [])
        updated_extra_auth_types = []
        is_extra_auth_api_key = False

        for auth in extra_auth_types:
            if auth['authentication_type'] == 'API_KEY':
                is_extra_auth_api_key = True
            updated_extra_auth_types.append(dict_keys_to_camel_case(auth))

        api_id = self.appsync_conn.create_graphql_api(
            name, auth_type=auth_type, tags=meta.get('tags'),
            user_pool_config=meta.get('user_pool_config'),
            open_id_config=meta.get('open_id_config'),
            lambda_auth_config=meta.get('lambda_auth_config'),
            log_config=meta.get('log_config'),
            xray_enabled=meta.get('xray_enabled'),
            extra_auth_types=updated_extra_auth_types)

        if auth_type == 'API_KEY' or is_extra_auth_api_key:
            self.appsync_conn.create_api_key(api_id)

        if schema_path := meta.get('schema_path'):
            schema_full_path = build_path(extract_to, schema_path)
            if not os.path.exists(schema_full_path):
                raise AssertionError(
                    f'\'{schema_full_path}\' file not found for '
                    f'AppSync \'{name}\'')

            with open(schema_full_path, 'r') as file:
                schema_definition = file.read()

            self.appsync_conn.create_schema(api_id, schema_definition)

        data_sources_meta = meta.get('data_sources', [])
        for data_source_meta in data_sources_meta:
            params = self._build_data_source_params_from_meta(data_source_meta)
            if not params:
                continue
            self.appsync_conn.create_data_source(api_id, **params)

        if resolvers_meta := meta.get('resolvers', []):
            for resolver_meta in resolvers_meta:
                params = self._build_resolver_params_from_meta(
                    resolver_meta, extract_to)
                if not params:
                    continue
                self.appsync_conn.create_resolver(api_id, **params)
        shutil.rmtree(extract_to, ignore_errors=True)
        _LOG.info(f'Created AppSync GraphQL API {api_id}')
        return self.describe_graphql_api(name=name, meta=meta, api_id=api_id)

    def _build_data_source_params_from_meta(self, source_meta: dict):
        source_name = source_meta.get('name')
        try:
            validate_params(
                source_name, source_meta, DATA_SOURCE_REQUIRED_PARAMS)
        except AssertionError as e:
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

        if source_type == 'AWS_LAMBDA' and source_config:
            region = source_config.pop('aws_region', None)
            lambda_name = source_config.pop('lambda_name', None)
            source_config['lambda_function_arn'] = self.build_lambda_arn(
                lambda_name, region)
        elif source_type == 'AMAZON_EVENTBRIDGE' and source_config:
            region = source_config.pop('aws_region')
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
    def _build_resolver_params_from_meta(resolver_meta, artifacts_path):
        type_name = resolver_meta.get('type_name')
        field_name = resolver_meta.get('field_name')
        try:
            validate_params(type_name + ':' + field_name, resolver_meta,
                            RESOLVER_REQUIRED_PARAMS)
        except AssertionError as e:
            _LOG.warning(str(e))
            _LOG.warning(f'Skipping resolver for type \'{type_name}\' '
                         f'and field \'{field_name}\'...')
            return

        _LOG.info(f'Altering resolver for type \'{type_name}\' and field '
                  f'\'{field_name}\'...')
        resolver_params = {
            'type_name': type_name,
            'field_name': field_name,
            'data_source_name': resolver_meta['data_source_name'],
            'kind': resolver_meta.get('kind', RESOLVER_DEFAULT_KIND)
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
            if not os.path.exists(code_path):
                raise AssertionError(
                    f"Resolver code file for type '{type_name}' and field "
                    f"'{field_name}' not found.")

            with open(code_path, 'r') as file:
                code = file.read()
            resolver_params['code'] = code
        else:
            _LOG.debug('Runtime is not JS')
            request_template_path = build_path(
                artifacts_path,
                resolver_meta.get('request_mapping_template_path'))
            if not os.path.exists(request_template_path):
                raise AssertionError(
                    f"Resolver request mapping template file for type "
                    f"'{type_name}' and field '{field_name}' not found.")
            else:
                with open(request_template_path, 'r') as file:
                    request_mapping_template = file.read()

            response_template_path = build_path(
                artifacts_path,
                resolver_meta.get('response_mapping_template_path'))
            if not os.path.exists(response_template_path):
                raise AssertionError(
                    f"Resolver response mapping template file for type "
                    f"'{type_name}' and field '{field_name}' not found.")
            else:
                with open(response_template_path, 'r') as file:
                    response_mapping_template = file.read()

            resolver_params['request_mapping_template'] = \
                request_mapping_template
            resolver_params['response_mapping_template'] = \
                response_mapping_template

        if max_batch_size := resolver_meta.get('max_batch_size'):
            resolver_params['max_batch_size'] = max_batch_size

        return resolver_params

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
        api = self.appsync_conn.get_graphql_api_by_name(name)
        if not api:
            raise AssertionError(f'{name} GraphQL API does not exist.')

        archive_path = meta['deployment_package']
        extract_to = self._extract_zip(archive_path, name)
        api_id = api['apiId']
        updated_extra_auth_types = []
        extra_auth_types = meta.get('extra_auth_types', [])

        for auth in extra_auth_types:
            updated_extra_auth_types.append(dict_keys_to_camel_case(auth))

        self.appsync_conn.update_graphql_api(
            api_id, name, auth_type=meta.get('primary_auth_type'),
            user_pool_config=meta.get('user_pool_config'),
            open_id_config=meta.get('open_id_config'),
            lambda_auth_config=meta.get('lambda_auth_config'),
            log_config=meta.get('log_config'),
            xray_enabled=meta.get('xray_enabled'),
            extra_auth_types=updated_extra_auth_types)

        if schema_path := meta.get('schema_path'):
            schema_full_path = build_path(extract_to, schema_path)
            if not os.path.exists(schema_full_path):
                raise AssertionError(
                    f'\'{schema_full_path}\' file not found for '
                    f'AppSync \'{name}\'')

            with open(schema_full_path, 'r') as file:
                schema_definition = file.read()

            self.appsync_conn.create_schema(api_id, schema_definition)

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
                            resolver_meta, extract_to)
                    if not params:
                        break
                    self.appsync_conn.update_resolver(api_id, **params)
                    existent_resolvers.remove(resolver)
                    break

            # create a new one
            if to_create:
                params = self._build_resolver_params_from_meta(
                            resolver_meta, extract_to)
                if not params:
                    continue
                self.appsync_conn.create_resolver(api_id, **params)

        for resolver in existent_resolvers:
            self.appsync_conn.delete_resolver(api_id,
                                              type_name=resolver['typeName'],
                                              field_name=resolver['fieldName'])

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
                    self.appsync_conn.update_data_source(api_id, **params)
                    existent_sources.remove(source)
                    break

            # create a new one
            if to_create:
                params = self._build_data_source_params_from_meta(source_meta)
                if not params:
                    continue
                self.appsync_conn.create_data_source(api_id, **params)

        for source in existent_sources:
            self.appsync_conn.delete_data_source(api_id, source['name'])

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
            raise AssertionError(
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