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

from syndicate.commons.log_helper import get_user_logger
from syndicate.connection.cloud_watch_connection import \
    get_lambda_log_group_name
from syndicate.core.constants import S3_PATH_NAME
from syndicate.core.resources.helper import validate_params
from syndicate.core.resources.lambda_resource import \
    (LAMBDA_CONCUR_QUALIFIER_VERSION, LambdaResource,
     LAMBDA_MAX_CONCURRENCY, PROVISIONED_CONCURRENCY,
     LAMBDA_CONCUR_QUALIFIER_ALIAS,
     DYNAMODB_TRIGGER_REQUIRED_PARAMS, SQS_TRIGGER_REQUIRED_PARAMS,
     CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS, S3_TRIGGER_REQUIRED_PARAMS,
     SNS_TRIGGER_REQUIRED_PARAMS, KINESIS_TRIGGER_REQUIRED_PARAMS)
from syndicate.core.resources.s3_resource import S3Resource
from .cf_cloudwatch_rule_converter import attach_rule_target
from .cf_dynamodb_table_converter import CfDynamoDbTableConverter
from .cf_iam_role_converter import CfIamRoleConverter
from .cf_resource_converter import CfResourceConverter
from .cf_s3_converter import CfS3Converter
from .cf_sns_converter import CfSnsConverter
from ..cf_transform_utils import \
    (to_logic_name, lambda_publish_version_logic_name,
     lambda_alias_logic_name, lambda_function_logic_name,
     iam_role_logic_name, dynamodb_table_logic_name,
     sqs_queue_logic_name, cloudwatch_rule_logic_name,
     s3_bucket_logic_name, sns_topic_logic_name,
     kinesis_stream_logic_name, lambda_layer_logic_name)

_LOG = get_user_logger()


class CfLambdaFunctionConverter(CfResourceConverter):

    def convert(self, name, meta):
        lambda_function = awslambda.Function(lambda_function_logic_name(name))
        lambda_function.FunctionName = meta['name']
        lambda_function.Code = awslambda.Code(
            S3Bucket=self.config.deploy_target_bucket,
            S3Key=meta[S3_PATH_NAME])
        lambda_function.Handler = meta['func_name']
        lambda_function.MemorySize = meta['memory']
        role_name = meta['iam_role_name']

        role = self.get_resource(iam_role_logic_name(role_name))
        _arn = None
        if not role:
            _LOG.warning(f'Role \'{role_name}\' was not found in '
                         f'build_meta.json. Building arn manually')
            iam_service = self.resources_provider.iam()
            role = role_name  # for kinesis trigger
            _arn = iam_service.iam_conn.build_role_arn(role_name)
        else:
            _arn = GetAtt(iam_role_logic_name(meta['iam_role_name']), 'Arn')
        lambda_function.Role = _arn
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
                layer_logic_name = lambda_layer_logic_name(layer_name)
                layer = self.get_resource(layer_logic_name)
                if not layer:
                    raise AssertionError("Lambda layer '{}' is not present "
                                         "in build meta.".format(layer_name))
                lambda_layers.append(layer.ref())
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
        lambda_version = None
        if publish_version:
            lambda_version = self._lambda_version(
                function=lambda_function,
                provisioned_concurrency=provisioned_concur)

        alias = meta.get('alias')
        lambda_alias = None
        if alias:
            lambda_alias = self._lambda_alias(
                function=lambda_function, alias=alias,
                version_logic_name=lambda_version.title,
                provisioned_concurrency=provisioned_concur)

        retention = meta.get('logs_expiration')
        if retention:
            group_name = get_lambda_log_group_name(lambda_name=name)
            self.template.add_resource(
                self._log_group(group_name=group_name,
                                retention_in_days=retention))
        event_sources = meta.get('event_sources')
        if event_sources:
            for trigger_meta in event_sources:
                if lambda_alias:
                    arn = lambda_alias.ref()
                elif lambda_version:
                    arn = lambda_version.ref()
                else:
                    arn = lambda_function.ref()

                trigger_type = trigger_meta['resource_type']
                func = self.CREATE_TRIGGER[trigger_type]
                func(self, name, arn, role, trigger_meta)

    def _create_dynamodb_trigger_from_meta(self, lambda_name, lambda_arn,
                                           role, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        DYNAMODB_TRIGGER_REQUIRED_PARAMS)
        table_name = trigger_meta['target_table']

        table = self.get_resource(dynamodb_table_logic_name(table_name))

        if not CfDynamoDbTableConverter.is_stream_enabled(table):
            CfDynamoDbTableConverter.configure_table_stream(table)
        self.template.add_resource(self._event_source_mapping(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            event_source_arn=table.get_att('StreamArn'),
            event_source_name=table_name,
            batch_size=trigger_meta['batch_size'],
            starting_position='LATEST'))

    def _create_sqs_trigger_from_meta(self, lambda_name, lambda_arn, role,
                                      trigger_meta):
        validate_params(lambda_name, trigger_meta, SQS_TRIGGER_REQUIRED_PARAMS)
        target_queue_name = trigger_meta['target_queue']

        queue_logic_name = sqs_queue_logic_name(target_queue_name)
        target_queue = self.get_resource(queue_logic_name)
        if not target_queue:
            _LOG.error('Queue {} does not exist'.format(target_queue))
            return
        self.template.add_resource(self._event_source_mapping(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            event_source_arn=target_queue.get_att('Arn'),
            event_source_name=target_queue_name,
            batch_size=trigger_meta['batch_size']))

    def _create_cloud_watch_trigger_from_meta(self, lambda_name, lambda_arn,
                                              role, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS)
        rule_name = trigger_meta['target_rule']
        rule = self.get_resource(cloudwatch_rule_logic_name(rule_name))

        attach_rule_target(rule=rule, target_arn=lambda_arn)
        permission = self.convert_lambda_permission(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            principal='events',
            source_arn=rule.get_att('Arn'),
            permission_qualifier=rule_name
        )
        self.template.add_resource(permission)

    def _create_s3_trigger_from_meta(self, lambda_name, lambda_arn, role,
                                     trigger_meta):
        validate_params(lambda_name, trigger_meta, S3_TRIGGER_REQUIRED_PARAMS)
        target_bucket_name = trigger_meta['target_bucket']

        bucket_logic_name = s3_bucket_logic_name(target_bucket_name)
        target_bucket = self.get_resource(bucket_logic_name)
        if not target_bucket:
            _LOG.error('S3 bucket {0} event source for lambda {1} '
                       'was not created.'.format(target_bucket, lambda_name))
            return
        permission = self.convert_lambda_permission(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            principal='s3',
            source_arn=S3Resource.get_bucket_arn(target_bucket_name),
            permission_qualifier=target_bucket_name
        )
        target_bucket.DependsOn = permission
        self.template.add_resource(permission)
        CfS3Converter.configure_event_source_for_lambda(
            bucket=target_bucket,
            lambda_arn=lambda_arn,
            events=trigger_meta['s3_events'],
            filter_rules=trigger_meta.get('filter_rules')
        )

    def _create_sns_topic_trigger_from_meta(self, lambda_name, lambda_arn,
                                            role, trigger_meta):
        validate_params(lambda_name, trigger_meta, SNS_TRIGGER_REQUIRED_PARAMS)
        topic_name = trigger_meta['target_topic']

        topic = self.get_resource(sns_topic_logic_name(topic_name))
        if not topic:
            raise AssertionError(
                'Topic does not exist: {0}.'.format(topic_name))

        # region = trigger_meta.get('region') TODO: support region param

        CfSnsConverter.subscribe(topic=topic,
                                 protocol='lambda',
                                 endpoint=lambda_arn)
        permission = self.convert_lambda_permission(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            principal='sns',
            source_arn=topic.ref(),
            permission_qualifier=topic_name
        )
        self.template.add_resource(permission)

    def _create_kinesis_stream_trigger_from_meta(self, lambda_name, lambda_arn,
                                                 role, trigger_meta):
        validate_params(lambda_name, trigger_meta,
                        KINESIS_TRIGGER_REQUIRED_PARAMS)

        stream_name = trigger_meta['target_stream']

        stream = self.get_resource(kinesis_stream_logic_name(stream_name))
        if not stream:
            _LOG.error('Kinesis stream does not exist: {0}.'
                       .format(stream_name))
            return

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
                    "Resource": stream.get_att('Arn')
                }
            ],
            "Version": "2012-10-17"
        }
        policy = CfIamRoleConverter.convert_inline_policy(
            role=role,
            policy_name=policy_name,
            policy_document=policy_document)
        self.template.add_resource(policy)
        event_mapping = self._event_source_mapping(
            lambda_arn=lambda_arn,
            lambda_name=lambda_name,
            event_source_arn=stream.get_att('Arn'),
            event_source_name=stream_name,
            batch_size=trigger_meta['batch_size'],
            starting_position=trigger_meta['starting_position'])
        event_mapping.DependsOn = policy
        self.template.add_resource(event_mapping)

    @staticmethod
    def _event_source_mapping(lambda_arn, lambda_name,
                              event_source_arn, event_source_name,
                              batch_size, starting_position=None):
        event_source = awslambda.EventSourceMapping(to_logic_name(
            'LambdaEventSourceMapping', lambda_name, event_source_name))
        event_source.BatchSize = batch_size
        event_source.Enabled = True
        event_source.EventSourceArn = event_source_arn
        event_source.FunctionName = lambda_arn
        if starting_position:
            event_source.StartingPosition = starting_position
        return event_source

    CREATE_TRIGGER = {
        'dynamodb_trigger': _create_dynamodb_trigger_from_meta,
        'cloudwatch_rule_trigger': _create_cloud_watch_trigger_from_meta,
        'eventbridge_rule_trigger': _create_cloud_watch_trigger_from_meta,
        's3_trigger': _create_s3_trigger_from_meta,
        'sns_topic_trigger': _create_sns_topic_trigger_from_meta,
        'kinesis_trigger': _create_kinesis_stream_trigger_from_meta,
        'sqs_trigger': _create_sqs_trigger_from_meta
    }

    def _lambda_version(self, function, provisioned_concurrency=None):
        version_name = lambda_publish_version_logic_name(function.FunctionName)
        lambda_version = awslambda.Version(version_name)
        lambda_version.FunctionName = Ref(function)
        self._add_provisioned_concur(
            resource=lambda_version,
            provisioned_concurrency=provisioned_concurrency,
            expected_qualifier=LAMBDA_CONCUR_QUALIFIER_VERSION)
        self.template.add_resource(lambda_version)
        return lambda_version

    def _lambda_alias(self, function, alias, version_logic_name,
                      provisioned_concurrency=None):
        alias_resource_name = \
            lambda_alias_logic_name(function_name=function.FunctionName,
                                    alias=alias)
        lambda_alias = awslambda.Alias(alias_resource_name)
        lambda_alias.FunctionName = Ref(function)
        lambda_alias.Name = alias
        lambda_alias.FunctionVersion = GetAtt(version_logic_name, 'Version') \
            if version_logic_name else '$LATEST'

        self._add_provisioned_concur(
            resource=lambda_alias,
            provisioned_concurrency=provisioned_concurrency,
            expected_qualifier=LAMBDA_CONCUR_QUALIFIER_ALIAS)
        self.template.add_resource(lambda_alias)
        return lambda_alias

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
        name = to_logic_name('LogsLogGroup', group_name)
        log_group = logs.LogGroup(name)
        log_group.LogGroupName = group_name
        log_group.RetentionInDays = retention_in_days
        return log_group

    @staticmethod
    def convert_lambda_permission(lambda_arn, lambda_name, principal,
                                  source_arn=None, permission_qualifier=''):
        lambda_permission = awslambda.Permission(to_logic_name(
            'LambdaPermission', lambda_name, principal, permission_qualifier))
        lambda_permission.FunctionName = lambda_arn
        lambda_permission.Action = 'lambda:InvokeFunction'
        lambda_permission.Principal = '{}.amazonaws.com'.format(principal)
        if source_arn:
            lambda_permission.SourceArn = source_arn
        return lambda_permission
