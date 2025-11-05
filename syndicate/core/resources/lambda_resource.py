"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import json
import re
import time
from pathlib import PurePath
from typing import Optional, Dict

from botocore.exceptions import ClientError

from syndicate.exceptions import ArtifactError, ResourceNotFoundError, \
    ParameterError, InvalidValueError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.helper import retry
from syndicate.core.build.bundle_processor import load_latest_deploy_output
from syndicate.core.build.meta_processor import S3_PATH_NAME
from syndicate.core.constants import DEFAULT_LOGS_EXPIRATION, \
    DYNAMO_DB_TRIGGER, CLOUD_WATCH_RULE_TRIGGER, EVENT_BRIDGE_RULE_TRIGGER, \
    S3_TRIGGER, SNS_TOPIC_TRIGGER, KINESIS_TRIGGER, SQS_TRIGGER, \
    DYNAMODB_TRIGGER_REQUIRED_PARAMS, SQS_TRIGGER_REQUIRED_PARAMS, \
    CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS, S3_TRIGGER_REQUIRED_PARAMS, \
    SNS_TRIGGER_REQUIRED_PARAMS, KINESIS_TRIGGER_REQUIRED_PARAMS
from syndicate.core.decorators import threading_lock
from syndicate.core.helper import unpack_kwargs, is_zip_empty
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (
    build_description_obj, validate_params, assert_required_params, if_updated)

LAMBDA_LAYER_REQUIRED_PARAMS = ['runtimes', 'deployment_package']

PROVISIONED_CONCURRENCY = 'provisioned_concurrency'

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

LAMBDA_MAX_CONCURRENCY = 'max_concurrency'
LAMBDA_CONCUR_QUALIFIER_ALIAS = 'ALIAS'
LAMBDA_CONCUR_QUALIFIER_VERSION = 'VERSION'
_LAMBDA_PROV_CONCURRENCY_QUALIFIERS = [LAMBDA_CONCUR_QUALIFIER_ALIAS,
                                       LAMBDA_CONCUR_QUALIFIER_VERSION]
SNAP_START = 'snap_start'
_APPLY_SNAP_START_VERSIONS = 'publishedversions'
_APPLY_SNAP_START_VERSIONS_SNAKE_CASE = 'published_versions'
_APPLY_SNAP_START_NONE = 'none'
_SNAP_START_CONFIGURATIONS = [_APPLY_SNAP_START_VERSIONS,
                              _APPLY_SNAP_START_VERSIONS_SNAKE_CASE,
                              _APPLY_SNAP_START_NONE]
_MIN_SNAP_START_SUPPORTED_RUNTIME = {
    "python": (3, 12),
    "java": (11,),
    "dotnet": (8,)
}

NOT_AVAILABLE = 'N/A'

_DOTNET_LAMBDA_SHARED_STORE_ENV = {
    'DOTNET_SHARED_STORE': '/opt/dotnetcore/store/'
}


class LambdaResource(BaseResource):

    def __init__(self, lambda_conn, s3_conn, cw_logs_conn, sns_res, sns_conn,
                 iam_conn, dynamodb_conn, sqs_conn, kinesis_conn,
                 cw_events_conn, cognito_idp_conn, rds_conn, region,
                 account_id, deploy_target_bucket) -> None:
        self.lambda_conn = lambda_conn
        self.s3_conn = s3_conn
        self.cw_logs_conn = cw_logs_conn
        self.sns_res = sns_res
        self.sns_conn = sns_conn
        self.iam_conn = iam_conn
        self.dynamodb_conn = dynamodb_conn
        self.sqs_conn = sqs_conn
        self.kinesis_conn = kinesis_conn
        self.cw_events_conn = cw_events_conn
        self.cognito_idp_conn = cognito_idp_conn
        self.rds_conn = rds_conn
        self.region = region
        self.account_id = account_id
        self.deploy_target_bucket = deploy_target_bucket

        self.dynamic_params_resolvers = {
            ('cognito_idp', 'id'):
                self.cognito_idp_conn.if_pool_exists_by_name,
            ('cognito_idp', 'client_id'):
                self.cognito_idp_conn.if_cup_client_exist,
            ('rds_db_cluster', 'endpoint'):
                self.rds_conn.get_db_cluster_endpoint,
            ('rds_db_cluster', 'reader_endpoint'):
                self.rds_conn.get_db_cluster_reader_endpoint,
            ('rds_db_cluster', 'master_user_secret_name'):
                self.rds_conn.get_db_cluster_master_user_secret_name
        }

    def qualifier_alias_resolver(self, lambda_def):
        return lambda_def['Alias']

    def get_existing_permissions(self, lambda_arn):
        return self.lambda_conn.get_existing_permissions(lambda_arn)

    def remove_permissions(self, lambda_arn, permissions_sids):
        return self.lambda_conn.remove_permissions(lambda_arn,
                                                   permissions_sids)

    def remove_permissions_by_resource_name(self, lambda_name, resource_name,
                                            all_permissions=True):
        """ Remove permissions to invoke lambda by resource name

        :param lambda_name: lambda name, arn or full arn
        :param resource_name: resource name, arn or full arn
        :param all_permissions: whether to delete all permissions for the
        specified resource or the first one only
        """
        lambda_permissions = self.get_existing_permissions(lambda_name)
        for statement in lambda_permissions:
            try:
                source_arn = statement['Condition']['ArnLike']['AWS:SourceArn']
            except KeyError:
                continue
            if resource_name in source_arn:
                self.lambda_conn.remove_one_permission(
                    function_name=lambda_name,
                    statement_id=statement['Sid'])
                if not all_permissions:
                    break

    def qualifier_version_resolver(self, lambda_def):
        latest_version_number = lambda_def['Configuration']['Version']
        if 'LATEST' in latest_version_number:
            all_versions = self.lambda_conn.list_function_versions(
                name=lambda_def['Configuration']['FunctionName'])
            bare_version_arns = [version.get('Version') for version in
                                 all_versions]
            bare_version_arns.sort()
            latest_version_number = bare_version_arns[-1]
        return latest_version_number

    _LAMBDA_QUALIFIER_RESOLVER = {
        LAMBDA_CONCUR_QUALIFIER_ALIAS: qualifier_alias_resolver,
        LAMBDA_CONCUR_QUALIFIER_VERSION: qualifier_version_resolver
    }

    def remove_concurrency_for_function(self, kwargs):
        assert_required_params(
            all_params=kwargs,
            required_params_names=['name'])
        self.lambda_conn.delete_function_concurrency_config(
            name=kwargs['name'])

    def setup_lambda_concur_alias_version(self, **kwargs):
        assert_required_params(
            all_params=kwargs,
            required_params_names=['name',
                                   'qualifier',
                                   'provisioned_level',
                                   'type'])

        name = kwargs.get('name')
        concur_type = kwargs.get('type')
        qualifier = kwargs.get('qualifier')
        provisioned_level = kwargs.get('provisioned_level')
        resp = self.lambda_conn.configure_provisioned_concurrency(
            name=name,
            qualifier=qualifier,
            concurrent_executions=provisioned_level)
        _LOG.info(
            f'Lambda {name} concurrency configuration status '
            f'of type {concur_type}:{qualifier}: {resp.get("Status")}')

    def setup_lambda_concur_function(self, **kwargs):
        assert_required_params(
            all_params=kwargs,
            required_params_names=['name',
                                   'provisioned_level',
                                   'type'])
        name = kwargs.get('name')
        provisioned_level = kwargs.get('provisioned_level')
        concur_type = kwargs.get('type')
        resp = self.lambda_conn.put_function_concurrency(
            function_name=name,
            concurrent_executions=provisioned_level)
        _LOG.info(
            f'Lambda {name} concurrency configuration of type {concur_type}:'
            f'{resp.get("ReservedConcurrentExecutions")}')

    def create_lambda(self, args):
        """ Create lambdas in pool in sub processes.
    
        :type args: list
        """
        return self.create_pool(self._create_lambda_from_meta, args)

    def update_lambda(self, args):
        return self.create_pool(self._update_lambda, args)

    def update_lambda_layer(self, args):
        return self.create_pool(self._update_lambda_layer, args)

    def describe_lambda(self, name, meta, response=None):
        if not response:
            response = self.lambda_conn.get_function(lambda_name=name)
        if not response:
            return {}

        aliases = list(self.lambda_conn.get_aliases(name))
        alias = aliases[0] if aliases else None
        arn = self.build_lambda_arn_with_alias(response, alias)

        del response['Configuration']['FunctionArn']
        return {
            arn: build_description_obj(response, name, meta)
        }

    def build_lambda_arn(self, name):
        arn = 'arn:aws:lambda:{0}:{1}:function:{2}'.format(self.region,
                                                           self.account_id,
                                                           name)
        return arn

    def resolve_lambda_arn_by_version_and_alias(self, name, version, alias):
        if version or alias:
            lambda_response = self.lambda_conn.get_function(name, version)
            return self.build_lambda_arn_with_alias(lambda_response, alias)
        else:
            return self.lambda_conn.get_function(name)['Configuration'][
                'FunctionArn']

    def add_invocation_permission(self, name, principal, source_arn=None,
                                  statement_id=None, exists_ok=False):
        return self.lambda_conn.add_invocation_permission(
            name=name,
            principal=principal,
            source_arn=source_arn,
            statement_id=statement_id,
            exists_ok=exists_ok
        )

    def get_invocation_permission(self, lambda_name, qualifier):
        policies = self.lambda_conn.get_policy(lambda_name=lambda_name,
                                               qualifier=qualifier)
        if not policies:
            _LOG.warning(f'No invocation permissions were found in '
                         f'lambda: {lambda_name} with qualifier: {qualifier}')
            return {}
        return json.loads(policies['Policy'])

    def remove_invocation_permissions(self, lambda_name, qualifier,
                                      ids_to_remove=None):
        self.lambda_conn.remove_invocation_permission(
            func_name=lambda_name, qualifier=qualifier,
            ids_to_remove=ids_to_remove)

    def build_lambda_arn_with_alias(self, response, alias=None):
        name = response['Configuration']['FunctionName']
        l_arn = self.build_lambda_arn(name=name)
        version = response['Configuration']['Version']
        arn = '{0}:{1}'.format(l_arn, alias or version)
        return arn

    def _setup_function_concurrency(self, name, meta):
        con_exec = meta.get(LAMBDA_MAX_CONCURRENCY)
        if con_exec:
            _LOG.debug('Going to set up concurrency executions')
            if self.check_concurrency_availability(con_exec):
                self.lambda_conn.put_function_concurrency(
                    function_name=name,
                    concurrent_executions=con_exec)
                _LOG.info(
                    f'Concurrency limit for lambda {name} '
                    f'is set to {con_exec}')

    def check_concurrency_availability(self, requested_concurrency):
        if not (isinstance(requested_concurrency, int)
                and requested_concurrency >= 0):
            _LOG.warn('The number of reserved concurrent executions '
                      'must be a non-negative integer.')
            return False
        unresolved_exec = \
            self.lambda_conn.get_unresolved_concurrent_executions()
        if requested_concurrency <= unresolved_exec:
            return True
        else:
            _LOG.warn(
                f'Account does not have such unresolved executions.'
                f' Current un - {unresolved_exec}')
            return False

    @unpack_kwargs
    @retry()
    def _create_lambda_from_meta(self, name, meta):
        from syndicate.core import CONFIG
        _LOG.debug('Creating lambda %s', name)
        req_params = ['iam_role_name', 'runtime', 'memory', 'timeout',
                      'func_name']
        # Lambda configuration
        validate_params(name, meta, req_params)

        key = meta[S3_PATH_NAME]
        key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                key).as_posix()
        if not self.s3_conn.is_file_exists(self.deploy_target_bucket,
                                           key_compound):
            raise ArtifactError(
                f"Error while creating lambda: '{name};"
                f"Deployment package '{key_compound}' does not exist "
                f"in '{self.deploy_target_bucket}' bucket"
            )

        lambda_def = self.lambda_conn.get_function(name)
        if lambda_def:
            _LOG.warn('%s lambda exists.', name)
            return self.describe_lambda(name, meta, lambda_def)

        role_name = meta['iam_role_name']
        role_arn = self.iam_conn.check_if_role_exists(role_name)
        if not role_arn:
            raise ResourceNotFoundError(
                f"Role '{role_name}' does not exist; "
                f"Lambda '{name}' failed to be configured."
            )

        dl_target_arn = self.get_dl_target_arn(meta=meta,
                                               region=self.region,
                                               account_id=self.account_id)

        publish_version = meta.get('publish_version', False)
        lambda_layers_arns = []
        layer_meta = meta.get('layers')
        if layer_meta:
            if 'dotnet' in meta['runtime'].lower():
                env_vars = meta.get('env_variables', {})
                env_vars.update(_DOTNET_LAMBDA_SHARED_STORE_ENV)
                meta['env_variables'] = env_vars
            for layer_name in layer_meta:
                layer_arn = self.lambda_conn.get_lambda_layer_arn(layer_name)
                if not layer_arn:
                    raise ResourceNotFoundError(
                        f"Could not link lambda layer '{layer_name}' to "
                        f"lambda '{name}' due to layer absence!"
                    )
                lambda_layers_arns.append(layer_arn)

        ephemeral_storage = meta.get('ephemeral_storage', 512)

        if meta.get('env_variables'):
            self._resolve_env_variables(meta.get('env_variables'))

        self.lambda_conn.create_lambda(
            lambda_name=name,
            func_name=meta['func_name'],
            role=role_arn,
            runtime=meta['runtime'].lower(),
            memory=meta['memory'],
            timeout=meta['timeout'],
            s3_bucket=self.deploy_target_bucket,
            s3_key=key_compound,
            env_vars=meta.get('env_variables'),
            vpc_sub_nets=meta.get('subnet_ids'),
            vpc_security_group=meta.get('security_group_ids'),
            dl_target_arn=dl_target_arn,
            tracing_mode=meta.get('tracing_mode'),
            publish_version=publish_version,
            layers=lambda_layers_arns,
            ephemeral_storage=ephemeral_storage,
            snap_start=self._resolve_snap_start(meta=meta),
            architectures=meta.get('architectures'),
            tags=meta.get('tags')
        )
        _LOG.debug('Lambda created %s', name)
        # AWS sometimes returns None after function creation, needs for
        # stability
        waiter = self.lambda_conn.get_waiter('function_exists')
        waiter.wait(FunctionName=name)

        self._resolve_log_group(lambda_name=name, meta=meta)

        lambda_def = self.__describe_lambda_by_version(
            name) if publish_version else self.lambda_conn.get_function(name)
        version = lambda_def['Configuration']['Version']
        self._setup_function_concurrency(name=name, meta=meta)

        # enabling aliases,
        # aliases can be enabled only and for $LATEST
        alias = meta.get('alias')
        if alias:
            _LOG.debug('Creating alias')
            _LOG.debug(self.lambda_conn.create_alias(function_name=name,
                                                     name=alias,
                                                     version=version))
        url_config = meta.get('url_config')
        if url_config:
            _LOG.info('Url config is found. Setting the function url')
            url = self.lambda_conn.set_url_config(
                function_name=name, auth_type=url_config.get('auth_type'),
                qualifier=alias, cors=url_config.get('cors'),
                principal=url_config.get('principal'),
                source_arn=url_config.get('source_arn')
            )
            USER_LOG.info(f'{name}:{alias if alias else ""} URL: {url}')

        arn = self.build_lambda_arn_with_alias(lambda_def, alias) \
            if publish_version or alias else \
            lambda_def['Configuration']['FunctionArn']
        _LOG.debug(f'Resolved lambda arn: {arn}')

        event_sources_meta = meta.get('event_sources', [])
        self.create_lambda_triggers(name, arn, role_name, event_sources_meta)

        if meta.get('max_retries') is not None:
            _LOG.debug('Setting lambda event invoke config')
            function_name = (name + ":" + alias) if alias else name
            invoke_config = self.lambda_conn.put_function_event_invoke_config(
                function_name=function_name,
                max_retries=meta.get('max_retries')
            )
            _LOG.debug(f'Created lambda invoke config: {invoke_config}')

        # concurrency configuration
        self._manage_provisioned_concurrency_configuration(
            function_name=name,
            meta=meta,
            lambda_def=lambda_def)
        return self.describe_lambda(name, meta, lambda_def)

    @staticmethod
    def get_dl_target_arn(meta, region, account_id):
        dl_type = meta.get('dl_resource_type')
        if dl_type:
            dl_type = dl_type.lower()
        dl_name = meta.get('dl_resource_name')
        dl_target_arn = 'arn:aws:{0}:{1}:{2}:{3}'.format(
            dl_type,
            region,
            account_id,
            dl_name) if dl_type and dl_name else None
        return dl_target_arn

    @unpack_kwargs
    def _update_lambda(self, name, meta, context):
        from syndicate.core import CONFIG
        _LOG.info('Updating lambda: {0}'.format(name))
        req_params = ['runtime', 'memory', 'timeout', 'func_name']

        validate_params(name, meta, req_params)

        key = meta[S3_PATH_NAME]
        key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                key).as_posix()
        if not self.s3_conn.is_file_exists(self.deploy_target_bucket,
                                           key_compound):
            raise ArtifactError(
                f"Deployment package '{key_compound}' does not exist "
                f"in '{self.deploy_target_bucket}' bucket'"
            )

        response = self.lambda_conn.get_function(name)
        if not response:
            raise ResourceNotFoundError(f"'{name}' lambda does not exist.")
        old_conf = response['Configuration']

        publish_version = meta.get('publish_version', False)

        self.lambda_conn.update_code_source(
            lambda_name=name,
            s3_bucket=self.deploy_target_bucket,
            s3_key=key_compound,
            publish_version=publish_version)

        role_name = meta['iam_role_name']
        role_arn = self.iam_conn.check_if_role_exists(role_name)
        if not role_arn:
            _LOG.warning('Execution role does not exist. Keeping the old one')
        role_arn = if_updated(role_arn, old_conf.get('Role'))
        handler = if_updated(meta.get('func_name'), old_conf.get('Handler'))
        env_vars = meta.get('env_variables', {})
        timeout = if_updated(meta.get('timeout'), old_conf.get('Timeout'))
        memory_size = if_updated(meta.get('memory_size'),
                                 old_conf.get('MemorySize'))

        old_subnets, old_security_groups, _ = self.lambda_conn.retrieve_vpc_config(
            old_conf)
        vpc_subnets = if_updated(set(meta.get('subnet_ids') or []),
                                 old_subnets)
        vpc_security_group = if_updated(
            set(meta.get('security_group_ids') or []), old_security_groups)
        runtime = if_updated(meta.get('runtime'), old_conf.get('Runtime'))
        ephemeral_storage = if_updated(
            meta.get('ephemeral_storage'),
            self.lambda_conn.retrieve_ephemeral_storage(old_conf))

        dl_type = meta.get('dl_resource_type')
        if dl_type:
            dl_type = dl_type.lower()
        dl_name = meta.get('dl_resource_name')

        dl_target_arn = 'arn:aws:{0}:{1}:{2}:{3}'.format(
            dl_type,
            self.region,
            self.account_id,
            dl_name) if dl_type and dl_name else None

        lambda_layers_arns = []
        layer_meta = meta.get('layers')
        if layer_meta:
            if 'dotnet' in meta['runtime'].lower():
                env_vars.update(_DOTNET_LAMBDA_SHARED_STORE_ENV)
                meta['env_variables'] = env_vars
            for layer_name in layer_meta:
                layer_arn = self.lambda_conn.get_lambda_layer_arn(layer_name)
                if not layer_arn:
                    raise ResourceNotFoundError(
                        f"Could not link lambda layer '{layer_name}' to "
                        f"lambda '{name}' due to layer absence!"
                    )
                lambda_layers_arns.append(layer_arn)

        if env_vars:
            self._resolve_env_variables(env_vars)

        tracing_mode = meta.get('tracing_mode')

        _LOG.info(f'Updating lambda {name} configuration')
        self.lambda_conn.update_lambda_configuration(
            lambda_name=name, role=role_arn, handler=handler,
            env_vars=env_vars,
            timeout=timeout, memory_size=memory_size, runtime=runtime,
            vpc_sub_nets=vpc_subnets, vpc_security_group=vpc_security_group,
            dead_letter_arn=dl_target_arn, layers=lambda_layers_arns,
            ephemeral_storage=ephemeral_storage,
            snap_start=self._resolve_snap_start(meta=meta),
            tracing_mode=tracing_mode
        )
        _LOG.info(f'Lambda configuration has been updated')

        # It seems to me that the waiter is not necessary here, the method
        # lambda_conn.update_lambda_configuration is the one that actually
        # waits. But still it does not make it worse :)
        _LOG.info(f'Initializing function updated waiter for {name}')
        waiter = self.lambda_conn.get_waiter('function_updated_v2')
        waiter.wait(FunctionName=name)
        _LOG.info(f'Waiting has finished')

        self._resolve_log_group(lambda_name=name, meta=meta)

        response = self.lambda_conn.get_function(name)
        _LOG.info(f'Lambda describe result: {response}')
        code_sha_256 = response['Configuration']['CodeSha256']
        publish_ver_response = self.lambda_conn.publish_version(
            function_name=name,
            code_sha_256=code_sha_256)
        updated_version = publish_ver_response['Version']
        _LOG.info(
            f'Version {updated_version} for lambda {name} published')

        alias_name = meta.get('alias')
        aliases = list(
            self.lambda_conn.get_aliases(function_name=name).keys()
        )
        if alias_name:
            if alias_name in aliases:
                self.lambda_conn.update_alias(
                    function_name=name,
                    alias_name=alias_name,
                    function_version=updated_version)
                _LOG.info(
                    f'Alias {alias_name} has been updated for lambda {name}')
            else:
                self.lambda_conn.create_alias(
                    function_name=name,
                    name=alias_name,
                    version=updated_version)
                _LOG.info(
                    f'Alias {alias_name} has been created for lambda {name}')
        for alias in aliases:
            if alias != alias_name:
                self.lambda_conn.delete_alias(
                    function_name=name,
                    name=alias
                )
                aliases.remove(alias)

        url_config = meta.get('url_config')
        if url_config:
            _LOG.info('URL config is found. Setting the function URL')
            url = self.lambda_conn.set_url_config(
                function_name=name, auth_type=url_config.get('auth_type'),
                qualifier=alias_name, cors=url_config.get('cors'),
                principal=url_config.get('principal'),
                source_arn=url_config.get('source_arn')
            )
            print(f'{name}:{alias_name if alias_name else ""}: {url}')
        else:
            existing_url = self.lambda_conn.get_url_config(
                function_name=name, qualifier=alias_name)
            if existing_url:
                _LOG.info('Going to delete existing URL config that is not '
                          'described in the lambda_config file')
                self.lambda_conn.delete_url_config(
                    function_name=name, qualifier=alias_name)

        arn = self.build_lambda_arn_with_alias(response, alias_name) \
            if publish_version or alias_name else \
            response['Configuration']['FunctionArn']
        _LOG.debug(f'Resolved lambda arn: {arn}')

        event_sources_meta = meta.get('event_sources', [])
        self.update_lambda_triggers(name, arn, role_name, event_sources_meta)

        if meta.get('max_retries') is not None:
            _LOG.debug('Updating lambda event invoke config')
            function_name = (name + ":" + alias_name) if alias_name else name
            try:
                _LOG.debug('Updating lambda event invoke config')
                invoke_config = \
                    self.lambda_conn.update_function_event_invoke_config(
                        function_name=function_name,
                        max_retries=meta.get('max_retries')
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    _LOG.debug('Lambda event invoke config is absent. '
                               'Creating a new one')
                    invoke_config = \
                        self.lambda_conn.put_function_event_invoke_config(
                            function_name=function_name,
                            max_retries=meta.get('max_retries')
                        )
                else:
                    raise e
            _LOG.debug(invoke_config)

        req_max_concurrency = meta.get(LAMBDA_MAX_CONCURRENCY)
        existing_max_concurrency = self.lambda_conn. \
            describe_function_concurrency(name=name)
        if req_max_concurrency and existing_max_concurrency:
            if existing_max_concurrency != req_max_concurrency:
                self._set_function_concurrency(name=name, meta=meta)
        elif not req_max_concurrency and existing_max_concurrency:
            self.lambda_conn.delete_function_concurrency_config(name=name)
        elif req_max_concurrency and not existing_max_concurrency:
            self._set_function_concurrency(name=name, meta=meta)

        self._manage_provisioned_concurrency_configuration(function_name=name,
                                                           meta=meta,
                                                           lambda_def=context)
        _LOG.info(f'Updating has finished for lambda {name}')
        return self.describe_lambda(name, meta, response)

    def _set_function_concurrency(self, name, meta):
        provisioned = self.lambda_conn. \
            describe_provisioned_concurrency_configs(name=name)
        if provisioned:
            self._delete_lambda_prov_concur_config(
                function_name=name,
                existing_config=provisioned)
        self._setup_function_concurrency(name=name, meta=meta)

    def _manage_provisioned_concurrency_configuration(self, function_name,
                                                      meta,
                                                      lambda_def=None):
        existing_configs = self.lambda_conn. \
            describe_provisioned_concurrency_configs(name=function_name)
        concurrency = meta.get(PROVISIONED_CONCURRENCY)

        if not existing_configs and not concurrency:
            # no existing config, no config in meta -> nothing to do
            return

        if existing_configs and concurrency:
            # todo check if required config already present
            if not lambda_def:
                lambda_def = self.lambda_conn.get_function(
                    lambda_name=function_name)

            self._delete_lambda_prov_concur_config(
                function_name=function_name,
                existing_config=existing_configs)
            self._create_lambda_prov_concur_config(
                function_name=function_name,
                meta=meta,
                concurrency=concurrency,
                lambda_def=lambda_def)
            return

        if not existing_configs and concurrency:
            # no existing but expected one - create
            self._create_lambda_prov_concur_config(
                function_name=function_name,
                meta=meta,
                concurrency=concurrency,
                lambda_def=lambda_def)
            return

        if existing_configs and not concurrency:
            # to delete existing one
            self._delete_lambda_prov_concur_config(
                function_name=function_name,
                existing_config=existing_configs)
            return

    def _delete_lambda_prov_concur_config(self, function_name,
                                          existing_config):
        if not existing_config:
            return
        for config in existing_config:
            qualifier = self._resolve_configured_existing_qualifier(config)
            self.lambda_conn.delete_provisioned_concurrency_config(
                name=function_name,
                qualifier=qualifier)
            _LOG.info(
                f'Existing provisioned concurrency configuration '
                f'set up on qualifier {qualifier} '
                f'was removed from lambda {function_name}')

    def _create_lambda_prov_concur_config(self, function_name, meta,
                                          concurrency,
                                          lambda_def=None):
        if not lambda_def:
            lambda_def = self.lambda_conn.get_function(
                lambda_name=function_name)
        qualifier = concurrency.get('qualifier')
        if not qualifier:
            raise ParameterError(
                "Parameter 'qualifier' is required for concurrency "
                "configuration but it is absent"
            )
        if qualifier not in _LAMBDA_PROV_CONCURRENCY_QUALIFIERS:
            raise InvalidValueError(
                f"Parameter 'qualifier' must be one of "
                f"'{_LAMBDA_PROV_CONCURRENCY_QUALIFIERS}', but it is equal "
                f"to '${qualifier}'"
            )

        resolved_qualifier = self._resolve_requested_qualifier(lambda_def,
                                                               meta,
                                                               qualifier)

        requested_provisioned_level = concurrency.get('value')
        if not requested_provisioned_level:
            raise ParameterError(
                "Parameter 'provisioned_level' is required for concurrency "
                "configuration but it is absent"
            )
        max_prov_limit = self.lambda_conn.describe_function_concurrency(
            name=function_name)
        if not max_prov_limit:
            max_prov_limit = self.lambda_conn. \
                get_unresolved_concurrent_executions()

        if requested_provisioned_level > max_prov_limit:
            raise InvalidValueError(
                f"Requested provisioned concurrency for "
                f"lambda '{function_name}' must not be greater "
                f"than function concurrency limit if any or "
                f"account unreserved concurrency. "
                f"Max is set to '{max_prov_limit}'; "
                f"Requested: '{requested_provisioned_level}'"
            )

        self.lambda_conn.configure_provisioned_concurrency(
            name=function_name,
            qualifier=resolved_qualifier,
            concurrent_executions=requested_provisioned_level)
        _LOG.info(f'Provisioned concurrency has been configured for lambda '
                  f'{function_name} of type {qualifier}, '
                  f'value {requested_provisioned_level}')

    def _resolve_requested_qualifier(self, lambda_def, meta, qualifier):
        if not qualifier:
            raise ParameterError(
                "Parameter 'qualifier' is required for concurrency "
                "configuration but it is absent"
            )
        if qualifier not in _LAMBDA_PROV_CONCURRENCY_QUALIFIERS:
            raise InvalidValueError(
                f"Parameter 'qualifier' must be one of "
                f"'{_LAMBDA_PROV_CONCURRENCY_QUALIFIERS}', but it is equal "
                f"to '${qualifier}'"
            )
        lambda_def['Alias'] = meta.get('alias')
        resolve_qualifier_req = lambda_def
        resolved_qualifier = self._LAMBDA_QUALIFIER_RESOLVER[qualifier](
            self, resolve_qualifier_req)
        return resolved_qualifier

    @staticmethod
    def _resolve_configured_existing_qualifier(existing_config):
        function_arn = existing_config.get('FunctionArn')
        parts = function_arn.split(':')
        return parts[-1]

    def _is_equal_lambda_layer(self, new_layer_sha, old_layer_name):
        import base64
        versions = self.lambda_conn.list_lambda_layer_versions(
            name=old_layer_name)
        for version in versions:
            old_layer = self.lambda_conn.get_lambda_layer_by_arn(
                version['LayerVersionArn'])
            if new_layer_sha == base64.b64decode(
                    old_layer['Content']['CodeSha256']):
                return old_layer

    def __describe_lambda_by_version(self, name):
        versions = self.lambda_conn.versions_list(name)
        # find the last created version
        version = max(
            [int(i['Version']) if i['Version'] != '$LATEST' else 0 for i in
             versions])
        if version != 0:
            return self.lambda_conn.get_function(name, str(version))
        else:
            return self.lambda_conn.get_function(name)

    @retry()
    def _create_dynamodb_trigger_from_meta(self, lambda_name, lambda_arn,
                                           role_name, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        DYNAMODB_TRIGGER_REQUIRED_PARAMS)
        table_name = trigger_meta['target_table']

        if not self.dynamodb_conn.describe_table(table_name):
            _LOG.warning(f'DynamoDB table \'{table_name}\' does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name} ')
            return

        batch_size, batch_window = self._resolve_batch_size_batch_window(
            trigger_meta)
        filters = trigger_meta.get('filters')

        if not self.dynamodb_conn.is_stream_enabled(table_name):
            self.dynamodb_conn.enable_table_stream(table_name)

        stream = self.dynamodb_conn.get_table_stream_arn(table_name)
        # TODO support another sub type
        event_source = next(iter(self.lambda_conn.list_event_sources(
            event_source_arn=stream, function_name=lambda_arn)), None)
        if event_source:
            _LOG.info(f'Lambda event source mapping for source arn '
                      f'{stream} and lambda arn {lambda_arn} was found. '
                      f'Updating it')
            self.lambda_conn.update_event_source(
                event_source['UUID'], function_name=lambda_arn,
                batch_size=batch_size,
                batch_window=batch_window, filters=filters)
        else:
            self.lambda_conn.add_event_source(
                lambda_arn, stream, batch_size=batch_size,
                batch_window=batch_window, start_position='LATEST',
                filters=filters
            )
        # start_position='LATEST' - in case we did not remove tables before
        _LOG.info('Lambda %s subscribed to dynamodb table %s', lambda_name,
                  table_name)

    @retry()
    def _create_sqs_trigger_from_meta(self, lambda_name, lambda_arn, role_name,
                                      trigger_meta):
        validate_params(lambda_name, trigger_meta, SQS_TRIGGER_REQUIRED_PARAMS)
        target_queue = trigger_meta['target_queue']
        function_response_types = trigger_meta.get(
            "function_response_types", [])
        batch_size, batch_window = self._resolve_batch_size_batch_window(
            trigger_meta)

        if not self.sqs_conn.get_queue_url(target_queue, self.account_id):
            _LOG.warning(f'SQS queue \'{target_queue}\' does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name} ')
            return

        queue_arn = 'arn:aws:sqs:{0}:{1}:{2}'.format(self.region,
                                                     self.account_id,
                                                     target_queue)

        event_source = next(iter(self.lambda_conn.list_event_sources(
            event_source_arn=queue_arn, function_name=lambda_arn)), None)
        if event_source:
            _LOG.info(f'Lambda event source mapping for source arn '
                      f'{queue_arn} and lambda arn {lambda_arn} was found. '
                      f'Updating it')
            self.lambda_conn.update_event_source(
                event_source['UUID'], function_name=lambda_arn,
                batch_size=batch_size,
                batch_window=batch_window,
                function_response_types=function_response_types)
        else:
            self.lambda_conn.add_event_source(
                lambda_arn, queue_arn, batch_size, batch_window,
                function_response_types=function_response_types
            )

        _LOG.info('Lambda %s subscribed to SQS queue %s', lambda_name,
                  target_queue)

    @retry()
    def _create_cloud_watch_trigger_from_meta(self, lambda_name, lambda_arn,
                                              role_name, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS)
        rule_name = trigger_meta['target_rule']
        # TODO add InputPath & InputTransformer if needed
        input_dict = trigger_meta.get('input')
        rule_arn = self.cw_events_conn.get_rule_arn(rule_name)
        if not rule_arn:
            _LOG.warning(f'Event Bridge rule \'{rule_name}\' does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name} ')
            return

        targets = self.cw_events_conn.list_targets_by_rule(rule_name)
        if lambda_arn not in map(lambda each: each.get('Arn'), targets):
            self.cw_events_conn.add_rule_target(rule_name, lambda_arn,
                                                input_dict)
            self.lambda_conn.add_invocation_permission(lambda_arn,
                                                       'events.amazonaws.com',
                                                       rule_arn)
            _LOG.info(f'Lambda {lambda_name} subscribed to cloudwatch rule '
                      f'{rule_name}')
        else:
            _LOG.info(f'Lambda {lambda_name} is already bound '
                      f'to cloudwatch rule {rule_name} as a target')

    @retry()
    # allow only sequential s3 trigger creation because it is done via 'put'
    # operation which will override any other concurrent request otherwise
    @threading_lock
    def _create_s3_trigger_from_meta(self, lambda_name, lambda_arn, role_name,
                                     trigger_meta):
        validate_params(lambda_name, trigger_meta, S3_TRIGGER_REQUIRED_PARAMS)
        target_bucket = trigger_meta['target_bucket']

        if not self.s3_conn.is_bucket_exists(target_bucket):
            _LOG.warning(f'S3 bucket {target_bucket} does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name} ')
            return

        bucket_arn = f'arn:aws:s3:::{target_bucket}'
        self.lambda_conn.add_invocation_permission(
            lambda_arn, 's3.amazonaws.com', bucket_arn)
        _LOG.debug(f'Waiting for activation of invoke-permission '
                   f'of {bucket_arn}')
        time.sleep(5)

        self.s3_conn.add_lambda_event_source(
            target_bucket, lambda_arn, trigger_meta)
        _LOG.info(f'Lambda {lambda_name} subscribed to '
                  f'S3 bucket {target_bucket}')

    @retry()
    def _create_sns_topic_trigger_from_meta(self, lambda_name, lambda_arn,
                                            role_name, trigger_meta):
        validate_params(lambda_name, trigger_meta, SNS_TRIGGER_REQUIRED_PARAMS)
        topic_name = trigger_meta['target_topic']

        if not self.sns_conn.get_topic_arn(topic_name):
            _LOG.warning(f'SNS topic {topic_name} does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name}')
            return

        region = trigger_meta.get('region')
        self.sns_res.create_sns_subscription_for_lambda(lambda_arn,
                                                        topic_name,
                                                        region)
        _LOG.info('Lambda %s subscribed to sns topic %s', lambda_name,
                  trigger_meta['target_topic'])

    @retry()
    def _create_kinesis_stream_trigger_from_meta(self, lambda_name, lambda_arn,
                                                 role_name, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        KINESIS_TRIGGER_REQUIRED_PARAMS)

        stream_name = trigger_meta['target_stream']
        stream_description = self.kinesis_conn.get_stream(stream_name)
        if not stream_description:
            _LOG.warning(f'Kinesis stream \'{stream_name}\' does not exist '
                         f'and could not be configured as a trigger '
                         f'for lambda {lambda_name} ')
            return

        stream_arn = stream_description['StreamARN']
        stream_status = stream_description['StreamStatus']
        # additional waiting for stream
        if stream_status != 'ACTIVE':
            _LOG.debug('Kinesis stream %s is not in active state,'
                       ' waiting for activation...', stream_name)
            time.sleep(120)

        # TODO policy should be moved to meta
        policy_name = '{0}KinesisTo{1}Lambda'.format(stream_name, lambda_name)
        policy_document = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        lambda_arn
                    ]
                },
                {
                    "Action": [
                        "kinesis:DescribeStreams",
                        "kinesis:DescribeStream",
                        "kinesis:ListStreams",
                        "kinesis:GetShardIterator",
                        "Kinesis:GetRecords"
                    ],
                    "Effect": "Allow",
                    "Resource": stream_arn
                }
            ],
            "Version": "2012-10-17"
        }
        self.iam_conn.attach_inline_policy(role_name=role_name,
                                           policy_name=policy_name,
                                           policy_document=policy_document)
        _LOG.debug('Inline policy %s is attached to role %s',
                   policy_name, role_name)
        _LOG.debug('Waiting for activation policy %s...', policy_name)
        time.sleep(10)

        self._add_kinesis_event_source(lambda_arn, stream_arn, trigger_meta)
        _LOG.info('Lambda %s subscribed to kinesis stream %s', lambda_name,
                  stream_name)

    @retry()
    def _add_kinesis_event_source(self, lambda_name, stream_arn, trigger_meta):
        self.lambda_conn.add_event_source(
            func_name=lambda_name, stream_arn=stream_arn,
            batch_size=trigger_meta['batch_size'],
            start_position=trigger_meta['starting_position'])

    CREATE_TRIGGER = {
        DYNAMO_DB_TRIGGER: _create_dynamodb_trigger_from_meta,
        CLOUD_WATCH_RULE_TRIGGER: _create_cloud_watch_trigger_from_meta,
        EVENT_BRIDGE_RULE_TRIGGER: _create_cloud_watch_trigger_from_meta,
        S3_TRIGGER: _create_s3_trigger_from_meta,
        SNS_TOPIC_TRIGGER: _create_sns_topic_trigger_from_meta,
        KINESIS_TRIGGER: _create_kinesis_stream_trigger_from_meta,
        SQS_TRIGGER: _create_sqs_trigger_from_meta
    }

    @retry()
    def _remove_cloud_watch_trigger(self, lambda_name, lambda_arn,
                                    trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS)

        target_rule = trigger_meta['target_rule']
        targets = []
        if self.cw_events_conn.get_rule(target_rule):
            targets = self.cw_events_conn.list_targets_by_rule(target_rule)
        for target in targets:
            if target['Arn'] == lambda_arn:
                # remove target so that this rule won't trigger lambda
                self.cw_events_conn.remove_targets(
                    rule_name=target_rule,
                    target_ids=[target['Id']]
                )
                _LOG.info(f'Lambda {lambda_name} unsubscribed from '
                          f'cloudwatch rule {target_rule}')
                break

        # remove event bridge permission to invoke lambda
        # to remove this trigger from lambda triggers section
        self.remove_permissions_by_resource_name(lambda_arn, target_rule)
        _LOG.info(f'Removed event bridge rule {target_rule} permissions to '
                  f'invoke lambda {lambda_name}')

    @retry()
    def _remove_sns_topic_trigger(self, lambda_name, lambda_arn, trigger_meta):
        validate_params(lambda_name, trigger_meta, SNS_TRIGGER_REQUIRED_PARAMS)

        target_topic = trigger_meta['target_topic']
        subscriptions = []
        topic_arn = self.sns_conn.get_topic_arn(name=target_topic)
        if topic_arn:
            subscriptions = self.sns_conn.list_subscriptions_by_topic(
                topic_arn=topic_arn)
        for subscription in subscriptions:
            if subscription['Protocol'] == 'lambda' \
                    and subscription['Endpoint'] == lambda_arn:
                # remove subscription so that this topic won't trigger lambda
                self.sns_conn.unsubscribe(
                    subscription_arn=subscription['SubscriptionArn'])
                _LOG.info(f'Lambda {lambda_name} unsubscribed '
                          f'from topic {target_topic}')
                break

        # remove sns permission to invoke lambda
        # to remove this trigger from lambda triggers section
        self.remove_permissions_by_resource_name(lambda_arn, target_topic)
        _LOG.info(f'Removed sns topic {target_topic} permissions to invoke '
                  f'lambda {lambda_name}')

    @retry()
    # allow only sequential s3 trigger deletion because it is done via 'put'
    # operation which will override any other concurrent request otherwise
    @threading_lock
    def _remove_s3_trigger(self, lambda_name, lambda_arn, trigger_meta):
        validate_params(lambda_name, trigger_meta, S3_TRIGGER_REQUIRED_PARAMS)

        target_bucket = trigger_meta['target_bucket']
        if self.s3_conn.is_bucket_exists(target_bucket):
            self.s3_conn.remove_lambda_event_source(
                target_bucket, lambda_arn, trigger_meta)
            _LOG.info(f'Lambda {lambda_name} unsubscribed from '
                      f's3 bucket {target_bucket}')

        # remove s3 permission to invoke lambda
        # to remove this trigger from lambda triggers section
        self.remove_permissions_by_resource_name(
            lambda_arn, target_bucket, all_permissions=False)
        _LOG.info(f'Removed s3 bucket {target_bucket} permissions to invoke '
                  f'lambda {lambda_name}')

    @retry()
    def _remove_sqs_trigger(self, lambda_name, lambda_arn, trigger_meta):
        validate_params(lambda_name, trigger_meta, SQS_TRIGGER_REQUIRED_PARAMS)

        target_queue = trigger_meta['target_queue']
        self._remove_event_source(
            lambda_name=lambda_name, lambda_arn=lambda_arn,
            event_source_name=target_queue)

    @retry()
    def _remove_dynamodb_trigger(self, lambda_name, lambda_arn, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        DYNAMODB_TRIGGER_REQUIRED_PARAMS)

        target_table = trigger_meta['target_table']
        self._remove_event_source(
            lambda_name=lambda_name, lambda_arn=lambda_arn,
            event_source_name=target_table)

    @retry()
    def _remove_kinesis_stream_trigger(self, lambda_name, lambda_arn,
                                       trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        KINESIS_TRIGGER_REQUIRED_PARAMS)

        target_stream = trigger_meta['target_stream']
        self._remove_event_source(
            lambda_name=lambda_name, lambda_arn=lambda_arn,
            event_source_name=target_stream)

    def _remove_event_source(self, lambda_name, lambda_arn, event_source_name):
        """ Remove event source from lambda triggers.
        SQS, DynamoDB, Kinezis, Kafka and MQ resources are considered
        as event sources according to AWS """
        uuid = None
        event_sources = self.lambda_conn.triggers_list(lambda_name=lambda_arn)
        for event_source in event_sources:
            if event_source_name in event_source['EventSourceArn']:
                uuid = event_source['UUID']
                break
        if uuid:
            self.lambda_conn.remove_event_source(uuid=uuid)
            _LOG.info(f'Lambda {lambda_name} unsubscribed from '
                      f'event source {event_source_name}')
        else:
            _LOG.warning(f'Could not remove event source {event_source_name} '
                         f'from lambda {lambda_name}.')

    REMOVE_TRIGGER = {
        DYNAMO_DB_TRIGGER: _remove_dynamodb_trigger,
        CLOUD_WATCH_RULE_TRIGGER: _remove_cloud_watch_trigger,
        EVENT_BRIDGE_RULE_TRIGGER: _remove_cloud_watch_trigger,
        S3_TRIGGER: _remove_s3_trigger,
        SNS_TOPIC_TRIGGER: _remove_sns_topic_trigger,
        KINESIS_TRIGGER: _remove_kinesis_stream_trigger,
        SQS_TRIGGER: _remove_sqs_trigger
    }

    def create_lambda_triggers(self, name, arn, role_name, event_sources_meta):
        for event_source in event_sources_meta:
            resource_type = event_source['resource_type']
            func = self.CREATE_TRIGGER[resource_type]
            func(self, name, arn, role_name, event_source)

    def update_lambda_triggers(self, name, arn, role_name, event_sources_meta):
        _, latest_output = load_latest_deploy_output(
            failsafe=True)
        latest_output = latest_output or {}

        prev_event_sources_meta = []
        for resource in latest_output:
            if arn in resource:
                resource_meta = latest_output[resource]['resource_meta']
                prev_event_sources_meta = \
                    resource_meta.get('event_sources', [])
                break

        # remove triggers that are absent or changed in new meta
        to_remove = [event_source for event_source in prev_event_sources_meta
                     if event_source not in event_sources_meta]
        self.remove_lambda_triggers(name, arn, to_remove)

        # create/update triggers
        self.create_lambda_triggers(name, arn, role_name, event_sources_meta)

    def remove_lambda_triggers(self, lambda_name, lambda_arn,
                               event_sources_meta):
        for event_source in event_sources_meta:
            resource_type = event_source['resource_type']
            func = self.REMOVE_TRIGGER[resource_type]
            func(self, lambda_name, lambda_arn, event_source)

    def remove_lambdas(self, args):
        return self.create_pool(self._remove_lambda, args)

    @unpack_kwargs
    @retry()
    def _remove_lambda(self, arn, config):
        # can't describe lambda event sources with $LATEST version in arn
        original_arn = arn
        arn = arn.replace(':$LATEST', '')
        lambda_name = config['resource_name']
        event_sources_meta = config['resource_meta'].get('event_sources', [])
        try:
            self.lambda_conn.delete_lambda(lambda_name,
                                           log_not_found_error=False)
            self.remove_lambda_triggers(lambda_name, arn, event_sources_meta)
            group_names = self.cw_logs_conn.get_log_group_names()
            for each in group_names:
                if lambda_name == each.split('/')[-1]:
                    self.cw_logs_conn.delete_log_group_name(each)
            _LOG.info('Lambda %s was removed.', lambda_name)
            return {original_arn: config}
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Lambda %s is not found', lambda_name)
                return {original_arn: config}
            else:
                raise e

    def create_lambda_layer(self, args):
        return self.create_pool(self.create_lambda_layer_from_meta, args)

    @unpack_kwargs
    def create_lambda_layer_from_meta(self, name, meta, context=None):
        """
        :param name:
        :param meta:
        :param context: because of usage in 'update' flow
        :return:
        """
        from syndicate.core import CONFIG
        validate_params(name, meta, LAMBDA_LAYER_REQUIRED_PARAMS)

        key = meta[S3_PATH_NAME]
        key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                key).as_posix()
        file_name = key.split('/')[-1]
        self.s3_conn.download_file(self.deploy_target_bucket, key_compound,
                                   file_name)
        if is_zip_empty(file_name):
            message = f'Can not create layer \'{name}\' because of empty ' \
                      f'deployment package zip file.'
            _LOG.error(message)
            return {}, [message]

        layer_arn = self.lambda_conn.get_lambda_layer_arn(name)
        if layer_arn:
            _LOG.warn(f"Layer '{name}' exists. Returning")
            return self.describe_lambda_layer(name, meta)

        with open(file_name, 'rb') as file_data:
            file_body = file_data.read()
        import hashlib
        hash_object = hashlib.sha256()
        hash_object.update(file_body)
        existing_version = self._is_equal_lambda_layer(hash_object.digest(),
                                                       name)
        if existing_version:
            existing_layer_arn = existing_version['LayerVersionArn']
            _LOG.info(f'Layer {name} with same content already '
                      f'exists in layer version {existing_layer_arn}.')
            return {
                existing_layer_arn: build_description_obj(
                    response=existing_version, name=name, meta=meta
                )}

        _LOG.debug(f'Creating lambda layer {name}')

        args = {'layer_name': name, 'runtimes': meta['runtimes'],
                's3_bucket': self.deploy_target_bucket,
                's3_key': PurePath(CONFIG.deploy_target_bucket_key_compound,
                                   meta[S3_PATH_NAME]).as_posix()}
        if meta.get('description'):
            args['description'] = meta['description']
        if meta.get('license'):
            args['layer_license'] = meta['license']
        if meta.get('architectures'):
            args['architectures'] = meta['architectures']
        response = self.lambda_conn.create_layer(**args)

        _LOG.info(f'Lambda Layer {name} version {response["Version"]} '
                  f'was successfully created')
        layer_arn = response['LayerVersionArn']
        del response['LayerArn']
        return {
            layer_arn: build_description_obj(
                response, name, meta)
        }

    @unpack_kwargs
    def _update_lambda_layer(self, name, meta, context=None):
        """
        :param name:
        :param meta:
        :param context: because of usage in 'update' flow
        :return:
        """
        from syndicate.core import CONFIG
        validate_params(name, meta, LAMBDA_LAYER_REQUIRED_PARAMS)

        key = meta[S3_PATH_NAME]
        key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                key).as_posix()
        file_name = key.split('/')[-1]
        self.s3_conn.download_file(self.deploy_target_bucket, key_compound,
                                   file_name)
        if is_zip_empty(file_name):
            message = f'Can not create layer \'{name}\' because of empty ' \
                      f'deployment package zip file.'
            _LOG.error(message)
            return {}, [message]

        layer_arn = self.lambda_conn.get_lambda_layer_arn(name)
        if not layer_arn:
            raise ResourceNotFoundError(
                f"Lambda layer '{name}' does not exist."
            )

        with open(file_name, 'rb') as file_data:
            file_body = file_data.read()
        import hashlib
        hash_object = hashlib.sha256()
        hash_object.update(file_body)
        existing_version = self._is_equal_lambda_layer(hash_object.digest(),
                                                       name)
        if existing_version:
            existing_layer_arn = existing_version['LayerVersionArn']
            _LOG.info(f'Layer {name} with same content already '
                      f'exists in layer version {existing_layer_arn}.')
            return {
                existing_layer_arn: build_description_obj(
                    response=existing_version, name=name, meta=meta
                )}

        _LOG.debug(f'Creating lambda layer {name}')

        args = {'layer_name': name, 'runtimes': meta['runtimes'],
                's3_bucket': self.deploy_target_bucket,
                's3_key': PurePath(CONFIG.deploy_target_bucket_key_compound,
                                   meta[S3_PATH_NAME]).as_posix()}
        if meta.get('description'):
            args['description'] = meta['description']
        if meta.get('license'):
            args['layer_license'] = meta['license']
        if meta.get('architectures'):
            args['architectures'] = meta['architectures']
        response = self.lambda_conn.create_layer(**args)

        _LOG.info(f'Lambda Layer {name} version {response["Version"]} '
                  f'was successfully created')
        layer_arn = response['LayerVersionArn']
        del response['LayerArn']
        return {
            layer_arn: build_description_obj(
                response, name, meta)
        }

    def remove_lambda_layers(self, args):
        return self.create_pool(self._remove_lambda_layers, args)

    @unpack_kwargs
    @retry()
    def _remove_lambda_layers(self, arn, config):
        layer_name = config['resource_name']
        _LOG.info('The latest lambda layer {0} version {1} was found.'.format(
            layer_name, arn.split(':')[-1]))
        layers_list = self.lambda_conn.list_lambda_layer_versions(layer_name)

        try:
            for l_arn in [layer['LayerVersionArn'] for layer in layers_list]:
                layer_version = l_arn.split(':')[-1]
                self.lambda_conn.delete_layer(l_arn, log_not_found_error=False)
                _LOG.info('Lambda layer {0} version {1} was removed.'.format(
                    layer_name, layer_version))
            return {arn: config}
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Lambda Layer {} is not found'.format(layer_name))
                return {arn: config}
            else:
                raise e

    def describe_lambda_layer(self, name, meta, response=None):
        if not response:
            layer_versions = self.lambda_conn.list_lambda_layer_versions(
                name=name
            )
            if not layer_versions:
                _LOG.warn(f'No versions available for layer {name}')
                return {}
            else:
                latest_version = max(
                    layer_versions, key=lambda x: x['Version'])
                response = self.lambda_conn.get_layer_version(
                    name=name,
                    version=latest_version['Version']
                )
        if not response:
            return {}

        arn = response['LayerVersionArn']
        del response['LayerArn']
        return {
            arn: build_description_obj(response, name, meta)
        }

    def _resolve_snap_start(self, meta: Dict[str, any]) -> Optional[str]:
        runtime: str = meta.get('runtime')
        if not runtime:
            return None

        runtime = runtime.lower()
        snap_start = meta.get(SNAP_START)
        if not snap_start:
            return None

        if not isinstance(snap_start, str):
            raise ParameterError(
                f'Invalid SnapStart value in "{SNAP_START}". '
                f'Expected a string, but got {type(snap_start).__name__}.'
            )

        if snap_start.lower() not in _SNAP_START_CONFIGURATIONS:
            raise ParameterError(
                f'Invalid SnapStart value in "{SNAP_START}". '
                f'Expected one of these: published_versions, '
                f'PublishedVersions, NONE. But got "{snap_start}".'
            )

        if not self.snap_start_supported_runtime(runtime):
            supported_runtimes = ", ".join(
                f"{k}{'.'.join(map(str, v))}+" for k, v in
                _MIN_SNAP_START_SUPPORTED_RUNTIME.items()
                )
            raise ParameterError(
                f'"{SNAP_START}" parameter is not available in runtime '
                f'"{runtime}". Supported runtimes are: {supported_runtimes}'
            )

        return 'None' if snap_start.lower() == _APPLY_SNAP_START_NONE \
            else 'PublishedVersions'

    @staticmethod
    def snap_start_supported_runtime(runtime: str) -> bool:
        """
        Splits runtime string into language and version parts
        and checks if the runtime is supported for SnapStart.
        """
        match = re.match(r"([a-z]+)([\d.]+)", runtime)
        if not match:
            return False

        lang, version_str = match.groups()
        version_parts = tuple(int(v) for v in version_str.split('.'))

        if lang not in _MIN_SNAP_START_SUPPORTED_RUNTIME:
            return False

        min_version = _MIN_SNAP_START_SUPPORTED_RUNTIME[lang]
        return version_parts >= min_version

    @staticmethod
    def _resolve_batch_size_batch_window(trigger_meta):
        batch_size = trigger_meta.get('batch_size')
        batch_window = trigger_meta.get('batch_window')
        if batch_size:
            if batch_size > 10 and not batch_window:
                batch_window = 1
                _LOG.info("The parameter 'batch_window' is set to the minimum "
                          f"default value ({batch_window}) because "
                          f"'batch_size' is greater than 10")
        return batch_size, batch_window

    def _resolve_log_group(self, lambda_name: str, meta: dict):

        log_group = self.cw_logs_conn.get_log_group_by_lambda_name(
            lambda_name=lambda_name
        )
        if log_group:
            log_group_name = log_group.get("logGroupName")
            _LOG.info(f"CloudWatch log group with name: {log_group_name}"
                      f" for lambda: {lambda_name} already exists.")

        if not log_group:
            _LOG.info(f"Cloud Watch log group for lambda: {lambda_name} does"
                      f" not exists. Creating new log group with name:"
                      f" aws/lambda/{lambda_name}")

            possible_retention = meta.get(
                'logs_expiration', DEFAULT_LOGS_EXPIRATION)
            try:
                retention = int(possible_retention)
            except (TypeError, ValueError):
                _LOG.warning(
                    f"Can't parse logs_expiration `{possible_retention}"
                    f" as int. Set default {DEFAULT_LOGS_EXPIRATION}"
                )
                retention = DEFAULT_LOGS_EXPIRATION

            if retention:
                self.cw_logs_conn.create_log_group_with_retention_days(
                    group_name=lambda_name,
                    retention_in_days=retention,
                    tags=meta.get('tags')
                )

    def _resolve_env_variables(self, env_vars):
        required_params = ['resource_name', 'resource_type', 'parameter']

        for key, value in env_vars.items():
            if isinstance(value, dict):
                resource_name = value.get('resource_name')
                resource_type = value.get('resource_type')
                parameter = value.get('parameter')

                if not all([resource_name, resource_type, parameter]):
                    missed_params = [p for p in required_params if
                                     value.get(p) is None]
                    env_vars[key] = NOT_AVAILABLE
                    USER_LOG.warn(
                        f"Unable to resolve value for environment variable "
                        f"'{key}' because of missing parameter/s. Required "
                        f"parameters: {required_params}; missed parameters/s "
                        f"{missed_params}."
                        f"The environment variable '{key}' will be configured "
                        f"with the value '{NOT_AVAILABLE}'."
                    )
                    continue

                _LOG.debug(
                    f"Going to resolve the value for the environment variable "
                    f"'{key}' by the parameter '{parameter}' of the resource "
                    f"type '{resource_type}' with the name '{resource_name}'.")

                resolver = self.dynamic_params_resolvers.get(
                    (resource_type, parameter)
                )

                if resolver is None:
                    USER_LOG.warn(
                        f"Currently resolving parameter '{parameter}' for the "
                        f"resource type '{resource_type}' is not supported.")
                    env_vars[key] = NOT_AVAILABLE
                else:
                    env_vars[key] = (resolver(resource_name) or NOT_AVAILABLE)

                if env_vars[key] == NOT_AVAILABLE:
                    USER_LOG.warn(
                        f"Unable to resolve parameter '{parameter}' for the "
                        f"resource type '{resource_type}' with name "
                        f"'{resource_name}'.")

                _LOG.debug(
                    f"The environment variable '{key}' will be configured "
                    f"with the value '{env_vars[key]}'."
                )
