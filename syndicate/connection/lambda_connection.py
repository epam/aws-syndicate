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
import uuid
from typing import Optional, List, Tuple, Iterable

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.constants import NONE_AUTH_TYPE, IAM_AUTH_TYPE
from syndicate.core.helper import dict_keys_to_capitalized_camel_case

_LOG = get_logger('lambda_connection')

AUTH_TYPE_TO_STATEMENT_ID = {
    NONE_AUTH_TYPE: 'FunctionURLAllowPublicAccess-Syndicate',
    IAM_AUTH_TYPE: 'FunctionURLAllowIAMAccess-Syndicate'
}


def _str_list_to_list(param, param_name):
    if isinstance(param, list):
        result = param
    elif isinstance(param, Iterable):
        result = list(param)
    elif isinstance(param, str):
        result = [param]
    else:
        raise ValueError(
            '{} must be a str or an iterable of strings.'.format(param_name))
    return result


@apply_methods_decorator(retry)
class LambdaConnection(object):
    """ Lambda connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('lambda', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Lambda connection.')

    def create_lambda(self, lambda_name, func_name,
                      role, s3_bucket, s3_key, runtime='python3.7', memory=128,
                      timeout=300, vpc_sub_nets=None, vpc_security_group=None,
                      env_vars=None, dl_target_arn=None, tracing_mode=None,
                      publish_version=False, layers=None,
                      ephemeral_storage=512, snap_start: str = None):
        """ Create Lambda method
        :type lambda_name: str
        :type func_name: str
        :param func_name: name of the entry point function
        :type role: str
        :param role: aws arn of role
        :type s3_bucket: str
        :type s3_key: str
        :type runtime: str
        :param memory: max limit of Lambda memory usage
        :param timeout: max limit of Lambda run time (300 - max value)
        :type vpc_sub_nets: list
        :type vpc_security_group: list
        :type env_vars: dict
        :param env_vars: {'string': 'string'}
        :type layers: list
        :param ephemeral_storage: amount of ephemeral storage between 512 MB
        and 10,240 MB
        :param snap_start: Optional[str] denotes `PublishedVersions`|`None`
        :return: response
        """
        layers = [] if layers is None else layers
        params = dict(FunctionName=lambda_name, Runtime=runtime,
                      Role=role, Handler=func_name,
                      Code={'S3Bucket': s3_bucket, 'S3Key': s3_key},
                      Description=' ', Timeout=timeout, MemorySize=memory,
                      Publish=publish_version, Layers=layers,
                      EphemeralStorage={'Size': ephemeral_storage})
        if env_vars:
            params['Environment'] = {'Variables': env_vars}
        if vpc_sub_nets and vpc_security_group:
            params['VpcConfig'] = {
                'SubnetIds': vpc_sub_nets,
                'SecurityGroupIds': vpc_security_group
            }
        if dl_target_arn:
            params['DeadLetterConfig'] = {
                'TargetArn': dl_target_arn
            }
        if tracing_mode:
            params['TracingConfig'] = {
                'Mode': tracing_mode
            }
        if snap_start:
            params['SnapStart'] = {
                'ApplyOn': snap_start
            }
        return self.client.create_function(**params)

    def set_url_config(self, function_name: str, qualifier: str = None,
                       auth_type: str = IAM_AUTH_TYPE, cors: dict = None,
                       principal: str = None, source_arn: str = None):
        _LOG.info(f'Setting url config for lambda: {function_name} with '
                  f'alias: {qualifier}')
        existing_url = self.get_url_config(function_name=function_name,
                                           qualifier=qualifier)
        if cors:
            # allow_origins is required for CORS
            if not cors.get('allow_origins'):
                cors['allow_origins'] = ['*']
        if not existing_url:
            _LOG.info('Existing url config was not found. Creating...')
            function_url = self.create_url_config(
                function_name=function_name, qualifier=qualifier,
                auth_type=auth_type, cors=cors)['FunctionUrl']
        else:
            _LOG.info('Existing url config was found. Updating...')
            existing_type = existing_url['AuthType']
            if existing_type != auth_type or existing_type == IAM_AUTH_TYPE:
                _LOG.warning('User has changed auth type or may have changed '
                             'principal or source arn. '
                             'Removing old permission')
                self.remove_one_permission(
                    function_name=function_name, qualifier=qualifier,
                    statement_id=AUTH_TYPE_TO_STATEMENT_ID[existing_type]
                )
            function_url = self.create_url_config(
                function_name=function_name, qualifier=qualifier,
                auth_type=auth_type, cors=cors, update=True)['FunctionUrl']

        if auth_type == NONE_AUTH_TYPE:
            _LOG.warning(f'Auth type is {NONE_AUTH_TYPE}. Setting '
                         f'the necessary resource-based policy')
            self.add_invocation_permission(
                name=function_name, principal='*', auth_type=auth_type,
                qualifier=qualifier, exists_ok=True,
                statement_id=AUTH_TYPE_TO_STATEMENT_ID[auth_type]
            )
        elif auth_type == IAM_AUTH_TYPE and principal:
            _LOG.warning(f'Auth type is {IAM_AUTH_TYPE}. Setting '
                         f'the necessary resource-based policy')
            self.add_invocation_permission(
                name=function_name, principal=principal,
                auth_type=auth_type, qualifier=qualifier,
                source_arn=source_arn,
                statement_id=AUTH_TYPE_TO_STATEMENT_ID[auth_type]
            )
        return function_url

    def put_function_event_invoke_config(self,
                                         function_name,
                                         max_retries=None):
        if max_retries is None:
            max_retries = 2
        return self.client.put_function_event_invoke_config(
            FunctionName=function_name,
            MaximumRetryAttempts=max_retries
        )

    def update_function_event_invoke_config(self,
                                            function_name,
                                            max_retries=None):
        if max_retries is None:
            max_retries = 2
        return self.client.update_function_event_invoke_config(
            FunctionName=function_name,
            MaximumRetryAttempts=max_retries
        )

    def delete_url_config(self, function_name: str, qualifier: str = None):
        params = dict(FunctionName=function_name)
        if qualifier:
            params['Qualifier'] = qualifier
        self.client.delete_function_url_config(**params)

    def create_url_config(self, function_name: str, qualifier: str = None,
                          auth_type: str = IAM_AUTH_TYPE, cors: dict = None,
                          update=False):
        params = dict(FunctionName=function_name,
                      AuthType=auth_type)
        if qualifier:
            params['Qualifier'] = qualifier
        if not cors:
            params['Cors'] = {}
        if cors and isinstance(cors, dict):
            params['Cors'] = dict_keys_to_capitalized_camel_case(cors)
        if update:
            return self.client.update_function_url_config(**params)
        else:
            return self.client.create_function_url_config(**params)

    def get_url_config(self, function_name: str, qualifier: str = None):
        params = dict(FunctionName=function_name)
        if qualifier:
            params['Qualifier'] = qualifier
        try:
            return self.client.get_function_url_config(**params)
        except ClientError as e:
            if e.response["Error"]["Code"] == 'ResourceNotFoundException':
                return None
            raise e

    def create_alias(self, function_name, name, version,
                     description=None, routing_config=None):
        """

        :param function_name: str
        :param name: str
        :param version: str
        :param description: str
        :param routing_config: dict str:int
        """
        params = dict(FunctionName=function_name, Name=name,
                      FunctionVersion=version)
        if description:
            params['Description'] = description
        if routing_config:
            params['RoutingConfig'] = routing_config

        return self.client.create_alias(**params)

    def get_alias(self, function_name, name):
        all_aliases = {}
        next_marker = 1  # to enter the loop
        while next_marker:
            req_param = {
                'FunctionName': function_name
            }
            if type(next_marker) == str:
                req_param['Marker'] = next_marker

            response = self.client.list_aliases(**req_param)

            all_aliases.update({item.get('Name'): item for item in
                                response.get('Aliases')})
            if all_aliases.get(name):
                return all_aliases.get(name)
            next_marker = response.get('NextMarker')

    def add_event_source(self, func_name, stream_arn, batch_size=15,
                         batch_window: Optional[int] = None,
                         start_position=None,
                         filters: Optional[List] = None):
        """ Create event source for Lambda
        :type func_name: str
        :type stream_arn: str
        :param batch_window: Optional[int]
        :param batch_size: max limit of Lambda event process in one time
        :param start_position: option for Lambda reading event mode
        :param filters: Optional[list]
        :return: response
        """
        params = dict(
            EventSourceArn=stream_arn, FunctionName=func_name,
            Enabled=True, BatchSize=batch_size
        )
        if batch_window:
            params['MaximumBatchingWindowInSeconds'] = batch_window
        if start_position:
            params['StartingPosition'] = start_position
        if filters:
            params['FilterCriteria'] = {'Filters': filters}

        response = self.client.create_event_source_mapping(**params)
        return response

    def list_event_sources(self, event_source_arn: Optional[str] = None,
                           function_name: Optional[str] = None) -> List:
        params = dict()
        if event_source_arn:
            params['EventSourceArn'] = event_source_arn
        if function_name:
            params['FunctionName'] = function_name
        return self.client.list_event_source_mappings(**params)['EventSourceMappings']

    def lambdas_list(self):
        """ Get all existing Lambdas.

        :return: list(if exists)
        """
        lambdas = []
        response = self.client.list_functions(MaxItems=1000)
        if 'Functions' in response:
            lambdas.extend(response['Functions'])
        marker = response.get('NextMarker')
        while marker:
            response = self.client.list_functions(Marker=marker,
                                                  MaxItems=1000)
            if 'Functions' in response:
                lambdas.extend(response['Functions'])
            marker = response.get('NextMarker')
        return lambdas

    def triggers_list(self, lambda_name):
        """ Get all existing triggers.

        :return: list(if exists)
        """
        mappings = []
        response = self.client.list_event_source_mappings(
            FunctionName=lambda_name)
        token = response.get('NextMarker')
        mappings.extend(response.get('EventSourceMappings'))
        while token:
            response = self.client.list_event_source_mappings(Marker=token)
            token = response.get('NextMarker')
            mappings.extend(response.get('EventSourceMappings'))
        return mappings

    def versions_list(self, function_name):
        versions = []
        response = self.client.list_versions_by_function(
            FunctionName=function_name)
        if 'Versions' in response:
            versions.extend(response['Versions'])
        marker = response.get('NextMarker')
        while marker:
            response = self.client.list_versions_by_function(Marker=marker)
            if 'Versions' in response:
                versions.extend(response['Versions'])
            marker = response.get('NextMarker')
        return versions

    def delete_lambda(self, func_name):
        """ Delete Lambda.

        :param func_name: str
        """
        self.client.delete_function(FunctionName=func_name)

    def remove_trigger(self, lambda_name):
        """ Remove trigger by name. Trigger has the same name as Lambda.

        :type lambda_name: str
        """
        triggers = self.triggers_list(lambda_name)
        for trigger in triggers:
            trigger_name = trigger['FunctionArn'].split(':')[-1]
            if trigger_name == lambda_name:
                try:
                    self.client.delete_event_source_mapping(
                        UUID=trigger['UUID'])
                except ClientError:
                    _LOG.error('Failed to delete trigger.', exc_info=True)

    def remove_lambdas(self):
        """ Removes all specified lambdas.

        :type lambda_names: list
        """
        list_functions = self.lambdas_list()
        for each in list_functions:
            try:
                self.delete_lambda(each['FunctionName'])
            except ClientError:
                _LOG.error(
                    'Failed to delete lambda %s', each['FunctionName'],
                    exc_info=True)

    def delete_trigger(self, uuid):
        """ Delete event source stream.

        :param uuid: str
        """
        self.client.delete_event_source_mapping(UUID=uuid)

    def remove_invocation_permission(self, func_name, qualifier=None,
                                     ids_to_remove=None):
        """Removes permission for API Gateway to be able to invoke lambda
        :param func_name: the name/arn of the function to remove
        permissions from
        :type func_name: str
        :param qualifier: alias or version of the function
        :type qualifier: str
        :param ids_to_remove: specific ids of permissions to remove. If not
        specified, all the function's permissions will be removed
        :type ids_to_remove: list
        """
        ids_to_remove = ids_to_remove or []
        if not ids_to_remove:
            policies = self.get_policy(lambda_name=func_name)
            if not policies:
                return
            policies = json.loads(policies['Policy'])
            policies_meta = policies['Statement']
            ids_to_remove = []
            for policy in policies_meta:
                if policy['Action'] == 'lambda:InvokeFunction':
                    ids_to_remove.append(policy['Sid'])

        for sid in ids_to_remove:
            self.remove_one_permission(function_name=func_name,
                                       statement_id=sid,
                                       qualifier=qualifier)

    def remove_one_permission(self, function_name, statement_id=None,
                              qualifier=None, soft=True):
        params = dict(FunctionName=function_name, StatementId=statement_id)
        if qualifier:
            params['Qualifier'] = qualifier
        try:
            self.client.remove_permission(**params)
        except ClientError as e:
            if e.response["Error"]["Code"] == 'ResourceNotFoundException' \
                    and soft:
                return None
            raise e

    def add_invocation_permission(self, name, principal, source_arn=None,
                                  statement_id=None, auth_type=None,
                                  qualifier=None, exists_ok=False):
        """ Add permission for something to be able to invoke lambda
        :type name: str
        :type source_arn: str
        :type principal: str
        :type statement_id: str
        :type auth_type: str, NONE|AWS_IAM
        :type qualifier: str
        """
        action = 'lambda:InvokeFunctionUrl' if auth_type \
            else 'lambda:InvokeFunction'
        if not statement_id:
            statement_id = str(uuid.uuid1())
        params = dict(FunctionName=name, StatementId=statement_id,
                      Action=action, Principal=principal)
        if auth_type:
            params['FunctionUrlAuthType'] = auth_type
        if source_arn:
            params['SourceArn'] = source_arn
        if qualifier:
            params['Qualifier'] = qualifier
        try:
            return self.client.add_permission(**params)
        except ClientError as e:
            if e.response["Error"]["Code"] == 'ResourceConflictException' \
                    and exists_ok:
                return None
            raise e

    def update_code_source(self, lambda_name, s3_bucket, s3_key,
                           publish_version):
        """ Update code source (s3 bucket + file link) for specified lambda.

        :type lambda_name: str
        :type s3_bucket: str
        :type s3_key: str
        :type publish_version: bool
        """
        self.client.update_function_code(FunctionName=lambda_name,
                                         S3Bucket=s3_bucket,
                                         S3Key=s3_key,
                                         Publish=publish_version)

    def update_event_source(self, uuid, function_name, batch_size,
                            batch_window=None, filters: Optional[List] = None):
        params = dict(
            UUID=uuid, FunctionName=function_name, BatchSize=batch_size
        )
        if batch_window is not None:
            params['MaximumBatchingWindowInSeconds'] = batch_window
        if filters is not None:
            params['FilterCriteria'] = {'Filters': filters}
        return self.client.update_event_source_mapping(**params)


    def get_function(self, lambda_name, qualifier=None):
        """ Get function info if it is exists,
        else - ResourceNotFoundException.

        :type lambda_name: name
        :param qualifier: Using this optional parameter to specify a function
        version or an alias name.
        :type qualifier: str
        """
        params = dict(FunctionName=lambda_name)
        if qualifier:
            params['Qualifier'] = qualifier
        try:
            return self.client.get_function(**params)
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_policy(self, lambda_name, qualifier=None):
        """ Returns the resource-based IAM policy for a function,
        version, or alias.

        :type lambda_name: name
        :param qualifier: Using this optional parameter to specify a function
        version or an alias name.
        :type qualifier: str
        """
        params = dict(FunctionName=lambda_name)
        if qualifier:
            params['Qualifier'] = qualifier
        try:
            return self.client.get_policy(**params)
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                return  # valid exception
            else:
                raise e

    def invoke_lambda(self, lambda_name, invocation_type='Event',
                      log_type='Tail', client_context='', payload=b'',
                      qualifier=''):
        """

        :param lambda_name:
        :param invocation_type: 'Event' | 'RequestResponse' | 'DryRun'
        :param log_type: 'None' | 'Tail'
        :type client_context: str
        :type payload: b'bytes' | file
        :type qualifier: str
        :return:
        """
        params = dict(FunctionName=lambda_name,
                      InvocationType=invocation_type,
                      LogType=log_type,
                      ClientContext=client_context,
                      Payload=payload)
        if qualifier:
            params['Qualifier'] = qualifier
        return self.client.invoke(**params)

    def get_lambda_configuration(self, lambda_name, qualifier=None):
        params = dict(FunctionName=lambda_name)
        if qualifier:
            params['Qualifier'] = qualifier

        return self.client.get_function_configuration(**params)

    def update_lambda_configuration(self, lambda_name, role=None, handler=None,
                                    description=None, timeout=None,
                                    memory_size=None, vpc_sub_nets=None,
                                    vpc_security_group=None,
                                    env_vars=None, runtime=None,
                                    dead_letter_arn=None, kms_key_arn=None,
                                    layers=None, ephemeral_storage=None,
                                    snap_start: str =None):
        params = dict(FunctionName=lambda_name)
        if ephemeral_storage:
            params['EphemeralStorage'] = {'Size': ephemeral_storage}
        if layers:
            params['Layers'] = layers
        if role:
            params['Role'] = role
        if handler:
            params['Handler'] = handler
        if description:
            params['Description'] = description
        if timeout:
            params['Timeout'] = timeout
        if memory_size:
            params['MemorySize'] = memory_size
        if vpc_sub_nets is not None:
            params.setdefault('VpcConfig', {}).update({
                'SubnetIds': _str_list_to_list(vpc_sub_nets, 'VPC_SUB_NETS')
            })
        if vpc_security_group is not None:
            params.setdefault('VpcConfig', {}).update({
                'SecurityGroupIds': _str_list_to_list(vpc_security_group,
                                                      'VPC_SECURITY_GROUPS')
            })
        env_vars = env_vars or {}
        params['Environment'] = {'Variables': env_vars}
        if runtime:
            params['Runtime'] = runtime
        if dead_letter_arn:
            params['DeadLetterConfig'] = {'TargetArn': dead_letter_arn}
        if kms_key_arn:
            params['KMSKeyArn'] = kms_key_arn
        if snap_start:
            params['SnapStart'] = {
                'ApplyOn': snap_start
            }
        return self.client.update_function_configuration(**params)

    def put_function_concurrency(self, function_name, concurrent_executions):
        return self.client.put_function_concurrency(
            FunctionName=function_name,
            ReservedConcurrentExecutions=concurrent_executions)

    def get_unresolved_concurrent_executions(self):
        return self.client.get_account_settings()['AccountLimit'][
            'UnreservedConcurrentExecutions']

    def publish_version(self, function_name, code_sha_256):
        return self.client.publish_version(
            FunctionName=function_name,
            CodeSha256=code_sha_256
        )

    def update_alias(self, function_name, alias_name, function_version):
        return self.client.update_alias(
            FunctionName=function_name,
            Name=alias_name,
            FunctionVersion=function_version
        )

    def create_layer(self, layer_name, s3_bucket, s3_key, runtimes,
                     description=None,
                     layer_license=None):
        kwargs = {'LayerName': layer_name, 'CompatibleRuntimes': runtimes,
                  'Content': {'S3Bucket': s3_bucket, 'S3Key': s3_key}}
        if description:
            kwargs['Description'] = description
        if layer_license:
            kwargs['LicenseInfo'] = layer_license
        return self.client.publish_layer_version(**kwargs)

    def get_lambda_layer_arn(self, name):
        lambda_layers = self.client.list_layers()
        for each in lambda_layers['Layers']:
            if each['LayerName'] == name:
                return each['LatestMatchingVersion']['LayerVersionArn']
        while lambda_layers.get('NextMarker'):
            lambda_layers = self.client.list_layers(
                Marker=lambda_layers.get('NextMarker'))
            for each in lambda_layers['Layers']:
                if each['LayerName'] == name:
                    return each['LatestMatchingVersion']['LayerVersionArn']

    def get_lambda_layer_by_arn(self, arn):
        return self.client.get_layer_version_by_arn(Arn=arn)

    def delete_layer(self, arn):
        version = arn.split(':')[len(arn.split(':')) - 1]
        arn = arn[:-len(version) - 1]
        return self.client.delete_layer_version(
            LayerName=arn,
            VersionNumber=int(version))

    def list_lambda_layer_versions(self, name, runtime=None):
        kwargs = {'LayerName': name}
        if runtime:
            kwargs['CompatibleRuntime'] = runtime
        response = self.client.list_layer_versions(**kwargs)
        versions = response['LayerVersions']

        while response.get('NextMarker'):
            kwargs['Marker'] = response['NextMarker']
            response = self.client.list_layer_versions(**kwargs)
            versions.extend(response['LayerVersions'])

        return versions

    def configure_provisioned_concurrency(self, name, qualifier,
                                          concurrent_executions):
        if type(concurrent_executions) is not int:
            raise AssertionError(
                f'Parameter `concurrent_executions` '
                f'must be type of int, but not {type(concurrent_executions)}')
        return self.client.put_provisioned_concurrency_config(
            FunctionName=name,
            Qualifier=qualifier,
            ProvisionedConcurrentExecutions=concurrent_executions
        )

    def get_provisioned_concurrency(self, name, qualifier):
        return self.client.get_provisioned_concurrency_config(
            FunctionName=name,
            Qualifier=qualifier
        )

    def describe_provisioned_concurrency_configs(self, name):
        configs = []
        response = self.client.list_provisioned_concurrency_configs(
            FunctionName=name
        )
        configs.extend(response.get('ProvisionedConcurrencyConfigs'))
        marker = response.get('NextMarker')
        while marker:
            response = self.client.list_provisioned_concurrency_configs(
                FunctionName=name,
                Marker=marker
            )
            configs.extend(response.get('ProvisionedConcurrencyConfigs'))
            marker = response.get('NextMarker')
        return configs

    def describe_function_concurrency(self, name):
        return self.client.get_function_concurrency(
            FunctionName=name
        ).get('ReservedConcurrentExecutions')

    def delete_function_concurrency_config(self, name):
        # client.delete_function_concurrency return 204 None in boto3 1.11.14
        self.client.delete_function_concurrency(
            FunctionName=name)

    def delete_provisioned_concurrency_config(self, name, qualifier):
        # client.delete_provisioned_concurrency_config return 204 None
        #   in boto3 1.11.14
        self.client.delete_provisioned_concurrency_config(
            FunctionName=name,
            Qualifier=qualifier
        )

    def list_function_versions(self, name):
        versions = []
        resp = self.client.list_versions_by_function(
            FunctionName=name,
            MaxItems=100
        )
        versions.extend(resp.get('Versions'))
        next_marker = resp.get('NextMarker')
        while next_marker:
            self.client.list_versions_by_function(
                FunctionName=name,
                MaxItems=100,
                Marker=next_marker
            )
            versions.extend(resp.get('Versions'))
            next_marker = resp.get('NextMarker')
        return versions

    def get_waiter(self, waiter_name):
        return self.client.get_waiter(waiter_name)

    def retrieve_vpc_config(self, response: dict) -> Tuple[set, set, Optional[str]]:
        """
        Retrieves subnets ids, security groups ids and vpc id from response
        received from lambda.get_function:
        response = {
            ...
            "VpcConfig": {
                "SubnetIds": [],
                "SecurityGroupIds": [],
                "VpcId": ""
            },
            ...
        }
        """
        _vpc = response.get('VpcConfig', {})
        _subnet_ids = set(_vpc.get('SubnetIds', []))
        _security_groups = set(_vpc.get('SecurityGroupIds', []))
        _vpc_id = _vpc.get('VpcId')
        return _subnet_ids, _security_groups, _vpc_id

    def retrieve_ephemeral_storage(self, response: dict) -> Optional[int]:
        """
        Works like the one above
        """
        return response.get('EphemeralStorage', {}).get('Size')
