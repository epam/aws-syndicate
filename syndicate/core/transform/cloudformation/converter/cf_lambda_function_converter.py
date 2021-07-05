"""
    Copyright 2021 EPAM Systems, Inc.

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
from troposphere import GetAtt, Ref, logs, awslambda

from syndicate.connection.cloud_watch_connection import \
    get_lambda_log_group_name
from syndicate.core.constants import S3_PATH_NAME
from syndicate.core.resources.lambda_resource import \
    (LAMBDA_CONCUR_QUALIFIER_VERSION, LambdaResource,
     LAMBDA_MAX_CONCURRENCY, PROVISIONED_CONCURRENCY,
     LAMBDA_CONCUR_QUALIFIER_ALIAS)
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_helper import (to_logic_name,
                                   lambda_publish_version_logic_name,
                                   lambda_alias_logic_name,
                                   lambda_function_logic_name)


class CfLambdaFunctionConverter(CfResourceConverter):

    def convert(self, name, meta):
        lambda_function = awslambda.Function(lambda_function_logic_name(name))
        lambda_function.FunctionName = meta['name']
        lambda_function.Code = awslambda.Code(
            S3Bucket=self.config.deploy_target_bucket,
            S3Key=meta[S3_PATH_NAME])
        lambda_function.Handler = meta['func_name']
        lambda_function.MemorySize = meta['memory']
        lambda_function.Role = GetAtt(to_logic_name(meta['iam_role_name']),
                                      'Arn')
        lambda_function.Runtime = meta['runtime'].lower()
        lambda_function.Timeout = meta['timeout']

        env_vars = meta.get('env_variables')
        if env_vars:
            lambda_function.Environment = \
                awslambda.Environment(Variables=env_vars)

        dl_target_arn = LambdaResource.get_dl_target_arn(
            meta=meta,
            region=self.config.region,
            account_id=self.config.account_id)
        if dl_target_arn:
            lambda_function.DeadLetterConfig = \
                awslambda.DeadLetterConfig(TargetArn=dl_target_arn)

        layer_meta = meta.get('layers')
        if layer_meta:
            lambda_layers = []
            for layer_name in layer_meta:
                lambda_layers.append(Ref(layer_name))
            lambda_function.Layers = lambda_layers

        vpc_sub_nets = meta.get('subnet_ids')
        vpc_security_group = meta.get('security_group_ids')
        if vpc_sub_nets and vpc_security_group:
            lambda_function.VpcConfig = awslambda.VPCConfig(
                SubnetIds=vpc_sub_nets,
                SecurityGroupIds=vpc_security_group)

        tracing_mode = meta.get('tracing_mode')
        if tracing_mode:
            lambda_function.TracingConfig = \
                awslambda.TracingConfig(Mode=tracing_mode)

        reserved_concur = meta.get(LAMBDA_MAX_CONCURRENCY)
        lambda_service = self.resources_provider.lambda_resource()
        if lambda_service.check_concurrency_availability(reserved_concur):
            lambda_function.ReservedConcurrentExecutions = reserved_concur

        self.template.add_resource(lambda_function)

        provisioned_concur = meta.get(PROVISIONED_CONCURRENCY)

        publish_version = meta.get('publish_version', False)
        version_resource = None
        if publish_version:
            version_resource = self._lambda_version(
                lambda_name=lambda_function.title,
                provisioned_concurrency=provisioned_concur)

        alias = meta.get('alias')
        if alias:
            self._lambda_alias(
                lambda_name=lambda_function.title, alias=alias,
                version_logic_name=version_resource.title,
                provisioned_concurrency=provisioned_concur)

        retention = meta.get('logs_expiration')
        if retention:
            group_name = get_lambda_log_group_name(lambda_name=name)
            self.template.add_resource(
                self._log_group(group_name=group_name,
                                retention_in_days=retention))
        # TODO: lambda event sources
        event_sources = meta.get('event_sources')

    def _lambda_version(self, lambda_name, provisioned_concurrency=None):
        version_name = lambda_publish_version_logic_name(lambda_name)
        lambda_version = awslambda.Version(version_name)
        lambda_version.FunctionName = Ref(lambda_name)
        self._add_provisioned_concur(
            resource=lambda_version,
            provisioned_concurrency=provisioned_concurrency,
            expected_qualifier=LAMBDA_CONCUR_QUALIFIER_VERSION)
        self.template.add_resource(lambda_version)
        return lambda_version

    def _lambda_alias(self, lambda_name, alias, version_logic_name,
                      provisioned_concurrency=None):
        alias_resource_name = \
            lambda_alias_logic_name(function_name=lambda_name,
                                    alias=alias)
        lambda_alias = awslambda.Alias(alias_resource_name)
        lambda_alias.FunctionName = Ref(lambda_name)
        lambda_alias.Name = alias
        lambda_alias.FunctionVersion = GetAtt(version_logic_name, 'Version') \
            if version_logic_name else '$LATEST'

        self._add_provisioned_concur(
            resource=lambda_alias,
            provisioned_concurrency=provisioned_concurrency,
            expected_qualifier=LAMBDA_CONCUR_QUALIFIER_ALIAS)
        self.template.add_resource(lambda_alias)

    @staticmethod
    def _add_provisioned_concur(resource, provisioned_concurrency,
                                expected_qualifier):
        if provisioned_concurrency:
            qualifier = provisioned_concurrency.get('qualifier')
            if qualifier == expected_qualifier:
                value = provisioned_concurrency.get('value')
                resource.ProvisionedConcurrencyConfig = \
                    awslambda.ProvisionedConcurrencyConfiguration(
                        ProvisionedConcurrentExecutions=value)

    @staticmethod
    def _log_group(group_name, retention_in_days):
        name = to_logic_name('{}LogGroup'.format(group_name))
        log_group = logs.LogGroup(name)
        log_group.LogGroupName = group_name
        log_group.RetentionInDays = retention_in_days
        return log_group
