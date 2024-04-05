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
import time
from pathlib import PurePath
from typing import Optional

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection.helper import retry
from syndicate.core.build.meta_processor import S3_PATH_NAME
from syndicate.core.constants import DEFAULT_LOGS_EXPIRATION
from syndicate.core.helper import (unpack_kwargs,
                                   exit_on_exception)
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (
    build_description_obj, validate_params, assert_required_params, if_updated)

LAMBDA_LAYER_REQUIRED_PARAMS = ['runtimes', 'deployment_package']

DYNAMODB_TRIGGER_REQUIRED_PARAMS = ['target_table', 'batch_size']
CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS = ['target_rule']
S3_TRIGGER_REQUIRED_PARAMS = ['target_bucket', 's3_events']
SQS_TRIGGER_REQUIRED_PARAMS = ['target_queue', 'batch_size']
SNS_TRIGGER_REQUIRED_PARAMS = ['target_topic']
KINESIS_TRIGGER_REQUIRED_PARAMS = ['target_stream', 'batch_size',
                                   'starting_position']

PROVISIONED_CONCURRENCY = 'provisioned_concurrency'

_LOG = get_logger('syndicate.core.resources.lambda_resource')
USER_LOG = get_user_logger()

LAMBDA_MAX_CONCURRENCY = 'max_concurrency'
LAMBDA_CONCUR_QUALIFIER_ALIAS = 'ALIAS'
LAMBDA_CONCUR_QUALIFIER_VERSION = 'VERSION'
_LAMBDA_PROV_CONCURRENCY_QUALIFIERS = [LAMBDA_CONCUR_QUALIFIER_ALIAS,
                                       LAMBDA_CONCUR_QUALIFIER_VERSION]
SNAP_START = 'snap_start'
_APPLY_SNAP_START_VERSIONS = 'PublishedVersions'
_APPLY_SNAP_START_NONE = 'None'
_SNAP_START_CONFIGURATIONS = [_APPLY_SNAP_START_VERSIONS,
                              _APPLY_SNAP_START_NONE]

DYNAMO_DB_TRIGGER = 'dynamodb_trigger'
CLOUD_WATCH_RULE_TRIGGER = 'cloudwatch_rule_trigger'
EVENT_BRIDGE_RULE_TRIGGER = 'eventbridge_rule_trigger'
S3_TRIGGER = 's3_trigger'
SNS_TOPIC_TRIGGER = 'sns_topic_trigger'
KINESIS_TRIGGER = 'kinesis_trigger'
SQS_TRIGGER = 'sqs_trigger'


class LambdaResource(BaseResource):

    def __init__(self, lambda_conn, s3_conn, cw_logs_conn, sns_conn,
                 iam_conn, dynamodb_conn, sqs_conn, kinesis_conn,
                 cw_events_conn, region, account_id,
                 deploy_target_bucket) -> None:
        self.lambda_conn = lambda_conn
        self.s3_conn = s3_conn
        self.cw_logs_conn = cw_logs_conn
        self.sns_conn = sns_conn
        self.iam_conn = iam_conn
        self.dynamodb_conn = dynamodb_conn
        self.sqs_conn = sqs_conn
        self.kinesis_conn = kinesis_conn
        self.cw_events_conn = cw_events_conn
        self.region = region
        self.account_id = account_id
        self.deploy_target_bucket = deploy_target_bucket

    def qualifier_alias_resolver(self, lambda_def):
        return lambda_def['Alias']

    def get_existing_permissions(self, lambda_arn):
        return self.lambda_conn.get_existing_permissions(lambda_arn)

    def remove_permissions(self, lambda_arn, permissions_sids):
        return self.lambda_conn.remove_permissions(lambda_arn,
                                                   permissions_sids)

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
        return self.create_pool(self.create_lambda_layer_from_meta, args)

    def describe_lambda(self, name, meta, response=None):
        if not response:
            response = self.lambda_conn.get_function(lambda_name=name)
        arn = self.build_lambda_arn_with_alias(response, meta.get('alias'))

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
        arn = '{0}:{1}'.format(l_arn, version)
        # override version if alias exists
        if alias:
            arn = '{0}:{1}'.format(l_arn, alias)
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
            raise AssertionError(f'Error while creating lambda: {name};'
                                 f'Deployment package {key_compound} does not exist '
                                 f'in {self.deploy_target_bucket} bucket')

        lambda_def = self.lambda_conn.get_function(name)
        if lambda_def:
            _LOG.warn('%s lambda exists.', name)
            return self.describe_lambda(name, meta, lambda_def)

        role_name = meta['iam_role_name']
        role_arn = self.iam_conn.check_if_role_exists(role_name)
        if not role_arn:
            raise AssertionError(f'Role {role_name} does not exist; '
                                 f'Lambda {name} failed to be configured.')

        dl_target_arn = self.get_dl_target_arn(meta=meta,
                                               region=self.region,
                                               account_id=self.account_id)

        publish_version = meta.get('publish_version', False)
        lambda_layers_arns = []
        layer_meta = meta.get('layers')
        if layer_meta:
            for layer_name in layer_meta:
                layer_arn = self.lambda_conn.get_lambda_layer_arn(layer_name)
                if not layer_arn:
                    raise AssertionError(
                        'Could not link lambda layer {} to lambda {} '
                        'due to layer absence!'.format(layer_name, name))
                lambda_layers_arns.append(layer_arn)

        ephemeral_storage = meta.get('ephemeral_storage', 512)

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
            architectures=meta.get('architectures')
        )
        _LOG.debug('Lambda created %s', name)
        # AWS sometimes returns None after function creation, needs for
        # stability
        waiter = self.lambda_conn.get_waiter('function_exists')
        waiter.wait(FunctionName=name)

        log_group_name = name
        possible_retention = meta.get('logs_expiration', DEFAULT_LOGS_EXPIRATION)
        try:
            retention = int(possible_retention)
        except (TypeError, ValueError):
            _LOG.warning(
                f"Can't parse logs_expiration `{possible_retention} as int."
                f" Set default {DEFAULT_LOGS_EXPIRATION}"
            )
            retention = DEFAULT_LOGS_EXPIRATION

        if retention:
            self.cw_logs_conn.create_log_group_with_retention_days(
                group_name=log_group_name,
                retention_in_days=retention
            )

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
            print(f'{name}:{alias if alias else ""}: {url}')

        arn = self.build_lambda_arn_with_alias(lambda_def, alias) \
            if publish_version or alias else \
            lambda_def['Configuration']['FunctionArn']
        _LOG.debug('arn value: ' + str(arn))

        if meta.get('event_sources'):
            for trigger_meta in meta.get('event_sources'):
                trigger_type = trigger_meta['resource_type']
                func = self.CREATE_TRIGGER[trigger_type]
                func(self, name, arn, role_name, trigger_meta)

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

    @exit_on_exception
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
            raise AssertionError(
                'Deployment package {0} does not exist '
                'in {1} bucket'.format(key_compound,
                                       self.deploy_target_bucket))

        response = self.lambda_conn.get_function(name)
        if not response:
            raise AssertionError('{0} lambda does not exist.'.format(name))
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
        env_vars = meta.get('env_variables')
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
            for layer_name in layer_meta:
                layer_arn = self.lambda_conn.get_lambda_layer_arn(layer_name)
                if not layer_arn:
                    raise AssertionError(
                        'Could not link lambda layer {} to lambda {} '
                        'due to layer absence!'.format(layer_name, name))
                lambda_layers_arns.append(layer_arn)

        _LOG.info(f'Updating lambda {name} configuration')
        self.lambda_conn.update_lambda_configuration(
            lambda_name=name, role=role_arn, handler=handler,
            env_vars=env_vars,
            timeout=timeout, memory_size=memory_size, runtime=runtime,
            vpc_sub_nets=vpc_subnets, vpc_security_group=vpc_security_group,
            dead_letter_arn=dl_target_arn, layers=lambda_layers_arns,
            ephemeral_storage=ephemeral_storage,
            snap_start=self._resolve_snap_start(meta=meta)
        )
        _LOG.info(f'Lambda configuration has been updated')

        # It seems to me that the waiter is not necessary here, the method
        # lambda_conn.update_lambda_configuration is the one that actually
        # waits. But still it does not make it worse :)
        _LOG.info(f'Initializing function updated waiter for {name}')
        waiter = self.lambda_conn.get_waiter('function_updated_v2')
        waiter.wait(FunctionName=name)
        _LOG.info(f'Waiting has finished')

        log_group_name = name
        possible_retention = meta.get('logs_expiration', DEFAULT_LOGS_EXPIRATION)
        try:
            retention = int(possible_retention)
        except (TypeError, ValueError):
            _LOG.warning(
                f"Can't parse logs_expiration `{possible_retention} as int."
                f" Set default {DEFAULT_LOGS_EXPIRATION}"
            )
            retention = DEFAULT_LOGS_EXPIRATION
        if retention is not None:
            self.cw_logs_conn.update_log_group_retention_days(
                group_name=log_group_name,
                retention_in_days=retention
            )

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
        if alias_name:
            alias = self.lambda_conn.get_alias(function_name=name,
                                               name=alias_name)
            if not alias:
                self.lambda_conn.create_alias(
                    function_name=name,
                    name=alias_name,
                    version=updated_version)
                _LOG.info(
                    f'Alias {alias_name} has been created for lambda {name}')
            else:
                self.lambda_conn.update_alias(
                    function_name=name,
                    alias_name=alias_name,
                    function_version=updated_version)
                _LOG.info(
                    f'Alias {alias_name} has been updated for lambda {name}')

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

        if meta.get('event_sources'):
            if alias_name:
                _arn = self.build_lambda_arn_with_alias(response, alias_name)
            else:
                _arn = response['Configuration']['FunctionArn']
            for trigger_meta in meta.get('event_sources'):
                trigger_type = trigger_meta['resource_type']
                func = self.CREATE_TRIGGER[trigger_type]
                func(self, name, _arn, role_name, trigger_meta)

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
            raise AssertionError('Parameter `qualifier` is required for '
                                 'concurrency configuration but it is absent')
        if qualifier not in _LAMBDA_PROV_CONCURRENCY_QUALIFIERS:
            raise AssertionError(
                f'Parameter `qualifier` must be one of '
                f'{_LAMBDA_PROV_CONCURRENCY_QUALIFIERS}, but it is equal '
                f'to ${qualifier}')

        resolved_qualifier = self._resolve_requested_qualifier(lambda_def,
                                                               meta,
                                                               qualifier)

        requested_provisioned_level = concurrency.get('value')
        if not requested_provisioned_level:
            raise AssertionError('Parameter `provisioned_level` is required '
                                 'for concurrency configuration but '
                                 'it is absent')
        max_prov_limit = self.lambda_conn.describe_function_concurrency(
            name=function_name)
        if not max_prov_limit:
            max_prov_limit = self.lambda_conn. \
                get_unresolved_concurrent_executions()

        if requested_provisioned_level > max_prov_limit:
            raise AssertionError(f'Requested provisioned concurrency for '
                                 f'lambda {function_name} must not be greater '
                                 f'than function concurrency limit if any or '
                                 f'account unreserved concurrency. '
                                 f'Max is set to {max_prov_limit}; '
                                 f'Requested: {requested_provisioned_level}')

        self.lambda_conn.configure_provisioned_concurrency(
            name=function_name,
            qualifier=resolved_qualifier,
            concurrent_executions=requested_provisioned_level)
        _LOG.info(f'Provisioned concurrency has been configured for lambda '
                  f'{function_name} of type {qualifier}, '
                  f'value {requested_provisioned_level}')

    def _resolve_requested_qualifier(self, lambda_def, meta, qualifier):
        if not qualifier:
            raise AssertionError('Parameter `qualifier` is required for '
                                 'concurrency configuration but it is absent')
        if qualifier not in _LAMBDA_PROV_CONCURRENCY_QUALIFIERS:
            raise AssertionError(f'Parameter `qualifier` must be one of '
                                 f'{_LAMBDA_PROV_CONCURRENCY_QUALIFIERS}, but it is equal '
                                 f'to ${qualifier}')
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
                                           role_name,
                                           trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        DYNAMODB_TRIGGER_REQUIRED_PARAMS)
        table_name = trigger_meta['target_table']
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
        batch_size, batch_window = self._resolve_batch_size_batch_window(
            trigger_meta)

        if not self.sqs_conn.get_queue_url(target_queue, self.account_id):
            _LOG.debug(f'Queue {target_queue} does not exist')
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
                batch_window=batch_window)
        else:
            self.lambda_conn.add_event_source(
                lambda_arn, queue_arn, batch_size, batch_window
            )

        _LOG.info('Lambda %s subscribed to SQS queue %s', lambda_name,
                  target_queue)

    @retry()
    def _create_cloud_watch_trigger_from_meta(self, lambda_name, lambda_arn,
                                              role_name,
                                              trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS)
        rule_name = trigger_meta['target_rule']
        # TODO add InputPath & InputTransformer if needed
        input_dict = trigger_meta.get('input')
        rule_arn = self.cw_events_conn.get_rule_arn(rule_name)
        if not rule_arn:
            _LOG.error(f'No Arn of \'{rule_name}\' rule name could be found.')
            return None

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
    def _create_s3_trigger_from_meta(self, lambda_name, lambda_arn, role_name,
                                     trigger_meta):
        validate_params(lambda_name, trigger_meta, S3_TRIGGER_REQUIRED_PARAMS)
        target_bucket = trigger_meta['target_bucket']

        if not self.s3_conn.is_bucket_exists(target_bucket):
            _LOG.error(
                f'S3 bucket {target_bucket} event source for lambda '
                f'{lambda_name} was not created.')
            return

        bucket_arn = 'arn:aws:s3:::{0}'.format(target_bucket)

        self.lambda_conn.add_invocation_permission(lambda_arn,
                                                   's3.amazonaws.com',
                                                   bucket_arn)
        _LOG.debug('Waiting for activation of invoke-permission of %s',
                   bucket_arn)

        time.sleep(5)

        self.s3_conn.configure_event_source_for_lambda(target_bucket,
                                                       lambda_arn,
                                                       trigger_meta[
                                                           's3_events'],
                                                       trigger_meta.get(
                                                           'filter_rules'))
        _LOG.info('Lambda %s subscribed to S3 bucket %s', lambda_name,
                  target_bucket)

    @retry()
    def _create_sns_topic_trigger_from_meta(self, lambda_name, lambda_arn,
                                            role_name,
                                            trigger_meta):
        validate_params(lambda_name, trigger_meta, SNS_TRIGGER_REQUIRED_PARAMS)
        topic_name = trigger_meta['target_topic']

        region = trigger_meta.get('region')
        self.sns_conn.create_sns_subscription_for_lambda(lambda_arn,
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
        self.lambda_conn.add_event_source(lambda_name, stream_arn,
                                          trigger_meta['batch_size'],
                                          trigger_meta['starting_position'])

    CREATE_TRIGGER = {
        DYNAMO_DB_TRIGGER: _create_dynamodb_trigger_from_meta,
        CLOUD_WATCH_RULE_TRIGGER: _create_cloud_watch_trigger_from_meta,
        EVENT_BRIDGE_RULE_TRIGGER: _create_cloud_watch_trigger_from_meta,
        S3_TRIGGER: _create_s3_trigger_from_meta,
        SNS_TOPIC_TRIGGER: _create_sns_topic_trigger_from_meta,
        KINESIS_TRIGGER: _create_kinesis_stream_trigger_from_meta,
        SQS_TRIGGER: _create_sqs_trigger_from_meta
    }

    def remove_lambdas(self, args):
        self.create_pool(self._remove_lambda, args)

    @unpack_kwargs
    @retry()
    def _remove_lambda(self, arn, config):
        lambda_name = config['resource_name']
        try:
            self.lambda_conn.delete_lambda(lambda_name)
            self.lambda_conn.remove_trigger(lambda_name)
            group_names = self.cw_logs_conn.get_log_group_names()
            for each in group_names:
                if lambda_name == each.split('/')[-1]:
                    self.cw_logs_conn.delete_log_group_name(each)
            _LOG.info('Lambda %s was removed.', lambda_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Lambda %s is not found', lambda_name)
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
        with open(file_name, 'rb') as file_data:
            file_body = file_data.read()
        import hashlib
        hash_object = hashlib.sha256()
        hash_object.update(file_body)
        existing_version = self._is_equal_lambda_layer(hash_object.digest(),
                                                       name)
        if existing_version:
            existing_layer_arn = existing_version['LayerVersionArn']
            _LOG.info('Layer {} with same content already '
                      'exists in layer version {}.'.format(name,
                                                           existing_layer_arn))
            return {
                existing_layer_arn: build_description_obj(
                    response=existing_version, name=name, meta=meta
                )}

        _LOG.debug('Creating lambda layer %s', name)

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

        _LOG.info(
            'Lambda Layer {0} version {1} was successfully created'.format(
                name, response['Version']))
        layer_arn = response['LayerArn'] + ':' + str(response['Version'])
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
            for arn in [layer['LayerVersionArn'] for layer in layers_list]:
                layer_version = arn.split(':')[-1]
                self.lambda_conn.delete_layer(arn)
                _LOG.info('Lambda layer {0} version {1} was removed.'.format(
                    layer_name, layer_version))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Lambda Layer {} is not found'.format(layer_name))
            else:
                raise e

    @staticmethod
    def _resolve_snap_start(meta: dict) -> Optional[str]:
        runtime: str = meta.get('runtime')
        if not runtime:
            return

        runtime = runtime.lower()
        snap_start = meta.get(SNAP_START, None)
        if snap_start and snap_start not in _SNAP_START_CONFIGURATIONS:
            values = ', '.join(map('"{}"'.format, _SNAP_START_CONFIGURATIONS))
            issue = f'must reflect one of the following values: {values}'
            _LOG.warn(f'If given "{SNAP_START}" - {issue}.')
            snap_start = None

        if snap_start and 'java' not in runtime:
            _LOG.warn(f'"{runtime}" runtime does support \'{SNAP_START}\'.')
            snap_start = None

        return snap_start

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
