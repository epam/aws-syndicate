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
import uuid

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('lambda_connection')


def _str_list_to_list(param, param_name):
    result = None
    if isinstance(param, list):
        result = param
    elif isinstance(param, str):
        result = [param]
    else:
        raise ValueError(
            '{} must be a str or a list of str.'.format(param_name))
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
                      role, s3_bucket, s3_key, runtime='python2.7', memory=128,
                      timeout=300, vpc_sub_nets=None, vpc_security_group=None,
                      env_vars=None, dl_target_arn=None, tracing_mode=None,
                      publish_version=False, layers=None):
        """ Create Lambda method.

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
        :return: response
        """
        layers = [] if layers is None else layers
        params = dict(FunctionName=lambda_name, Runtime=runtime,
                      Role=role, Handler=func_name,
                      Code={'S3Bucket': s3_bucket, 'S3Key': s3_key},
                      Description=' ', Timeout=timeout, MemorySize=memory,
                      Publish=publish_version, Layers=layers)
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
        return self.client.create_function(**params)

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
                         start_position=None):
        """ Create event source for Lambda.

        :type func_name: str
        :type stream_arn: str
        :param batch_size: max limit of Lambda event process in one time
        :param start_position: option for Lambda reading event mode
        :return: response
        """
        params = dict(EventSourceArn=stream_arn,
                      FunctionName=func_name,
                      Enabled=True,
                      BatchSize=batch_size)

        if start_position:
            params['StartingPosition'] = start_position

        response = self.client.create_event_source_mapping(**params)
        return response

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

    def add_invocation_permission(self, name, principal, source_arn=None,
                                  statement_id=None):
        """ Add permission for something to be able invoke lambda.

        :type name: str
        :type source_arn: str
        :type principal: str
        :type statement_id: str
        """
        if not statement_id:
            statement_id = str(uuid.uuid1())
        params = dict(FunctionName=name, StatementId=statement_id,
                      Action='lambda:InvokeFunction', Principal=principal)
        if source_arn:
            params['SourceArn'] = source_arn
        self.client.add_permission(**params)

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

    def update_event_source(self, lambda_name, batch_size):
        """ Update batch size of lambda event source stream.

        :type lambda_name: str
        :type batch_size: int
        """
        triggers = self.triggers_list(lambda_name)
        for trigger in triggers:
            trigger_name = trigger['FunctionArn'].split(':')[-1]
            if trigger_name == lambda_name:
                return self.client.update_event_source_mapping(
                    UUID=trigger['UUID'],
                    FunctionName=lambda_name,
                    Enabled=True,
                    BatchSize=batch_size
                )

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
                pass  # valid exception
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
                                    layers=None):
        params = dict(FunctionName=lambda_name)
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
        if vpc_sub_nets:
            vpc_sub_nets = _str_list_to_list(vpc_sub_nets, 'VPC_SUB_NETS')
        if vpc_security_group:
            vpc_sub_nets = _str_list_to_list(vpc_security_group,
                                             'VPC_SECURITY_GROUPS')
        if vpc_sub_nets and vpc_security_group:
            params['VpcConfig'] = {
                'SubnetIds': vpc_sub_nets,
                'SecurityGroupIds': vpc_security_group
            }
        if env_vars:
            params['Environment'] = {'Variables': env_vars}
        if runtime:
            params['Runtime'] = runtime
        if dead_letter_arn:
            params['DeadLetterConfig'] = {'TargetArn': dead_letter_arn}
        if kms_key_arn:
            params['KMSKeyArn'] = kms_key_arn
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
            response = self.client.list_layer_versions(kwargs)
            versions.append(response['LayerVersions'])

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
