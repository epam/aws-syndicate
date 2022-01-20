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
import json

from syndicate.commons.log_helper import get_logger
from syndicate.connection.cloud_watch_connection import \
    get_lambda_log_group_name
from syndicate.core.resources.helper import validate_params
from syndicate.core.resources.lambda_resource import LAMBDA_MAX_CONCURRENCY, \
    PROVISIONED_CONCURRENCY, DYNAMODB_TRIGGER_REQUIRED_PARAMS, \
    SQS_TRIGGER_REQUIRED_PARAMS, CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS, \
    S3_TRIGGER_REQUIRED_PARAMS, SNS_TRIGGER_REQUIRED_PARAMS, \
    KINESIS_TRIGGER_REQUIRED_PARAMS
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name, lambda_layer_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_ref_to_lambda_layer_arn, build_function_arn_ref, \
    build_dynamo_db_stream_arn_ref, build_cloud_watch_event_rule_name_ref, \
    build_sns_topic_arn_ref, build_kinesis_stream_arn_ref, build_role_id_ref, \
    build_sqs_queue_arn_ref, build_bucket_id_ref, build_bucket_arn_ref, \
    build_function_name_ref, build_lambda_version_ref, \
    build_lambda_alias_name_ref, build_role_arn_ref

_LOG = get_logger(
    'syndicate.core.transform.terraform.converter.lambda_converter')

REQUIRED_PARAMS = ['iam_role_name', 'runtime', 'memory', 'timeout',
                   'func_name']


class LambdaConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        validate_params(name, resource, REQUIRED_PARAMS)

        function_name = resource.get('func_name')
        runtime = resource.get('runtime')
        memory = resource.get('memory')
        timeout = resource.get('timeout')
        env_variables = resource.get('env_variables')
        publish_version = resource.get('publish_version', False)
        subnet_ids = resource.get('subnet_ids', [])
        security_group_ids = resource.get('security_group_ids', [])

        s3_path = resource.get('s3_path')
        s3_bucket = self.config.deploy_target_bucket

        iam_role_name = resource.get('iam_role_name')
        iam_conn = self.resources_provider.iam().iam_conn
        role_arn = iam_conn.check_if_role_exists(iam_role_name)
        if not role_arn:
            iam_role = self.template.get_resource_by_name(iam_role_name)
            if not iam_role:
                raise AssertionError(f'Role {iam_role_name} does not exist; '
                                     f'Lambda {name} failed to be configured.')
            role_arn = build_role_arn_ref(iam_role_name)

        lambda_layers_arns = []
        layer_meta = resource.get('layers')
        if layer_meta:
            for layer_name in layer_meta:
                layer = self.template.get_resource_by_name(
                    lambda_layer_name(layer_name=layer_name))
                if not layer:
                    raise AssertionError(
                        f"Lambda layer '{layer_name}' is not present "
                        "in build meta.")
                layer_ref = build_ref_to_lambda_layer_arn(
                    layer_name=layer_name)
                lambda_layers_arns.append(layer_ref)

        retention = resource.get('logs_expiration')
        if retention:
            log_group = cloud_watch_log_group(lambda_name=function_name,
                                              retention=retention)
            self.template.add_cloud_watch_log_group(meta=log_group)

        reserved_concur = resource.get(LAMBDA_MAX_CONCURRENCY)
        lambda_service = self.resources_provider.lambda_resource()
        if not lambda_service.check_concurrency_availability(reserved_concur):
            reserved_concur = None

        aws_lambda = template_for_lambda(lambda_name=name,
                                         function_name=name,
                                         runtime=runtime,
                                         role_arn=role_arn,
                                         handler=function_name,
                                         memory=memory,
                                         timeout=timeout,
                                         env_variables=env_variables,
                                         publish=publish_version,
                                         subnet_ids=subnet_ids,
                                         security_group_ids=security_group_ids,
                                         reserved_concurrent_executions=reserved_concur,
                                         s3_bucket=s3_bucket,
                                         s3_key=s3_path)
        self.template.add_aws_lambda(meta=aws_lambda)
        self.configure_concurrency(resource=resource,
                                   function_name=name)
        self.process_event_sources(lambda_name=name, resource=resource,
                                   role=iam_role_name)

    def configure_concurrency(self, resource, function_name):
        provisioned_concur = resource.get(PROVISIONED_CONCURRENCY)
        publish_version = resource.get('publish_version', False)
        if publish_version:
            if provisioned_concur:
                res_name = 'concurrency_config_version'
                concurrency = provisioned_concurrency_config_with_lambda_version(
                    name=res_name,
                    function_name=function_name,
                    provisioned_concur=provisioned_concur)
                self.template.add_aws_lambda_provisioned_concurrency_config(
                    meta=concurrency)
                return
        alias = resource.get('alias')
        if alias:
            alias_resource_name = f'{function_name}_{alias}'
            alias_template = template_for_alias(alias_name=alias,
                                                resource_name=alias_resource_name,
                                                function_name=function_name)
            self.template.add_aws_lambda_alias(meta=alias_template)

            if provisioned_concur:
                res_name = 'concurrency_config_alias'
                concurrency = provisioned_concurrency_config_with_lambda_alias(
                    name=res_name, function_name=function_name,
                    provisioned_concur=provisioned_concur,
                    alias_name=alias_resource_name)
                self.template.add_aws_lambda_provisioned_concurrency_config(
                    meta=concurrency)

    def process_event_sources(self, lambda_name, resource, role):
        event_sources = resource.get('event_sources')
        if event_sources:
            for trigger_meta in event_sources:
                trigger_type = trigger_meta['resource_type']
                starting_position = trigger_meta.get('starting_position')
                if not starting_position:
                    starting_position = 'LATEST'

                func = self.CREATE_TRIGGER[trigger_type]
                func(self, lambda_name=lambda_name,
                     trigger_meta=trigger_meta,
                     starting_position=starting_position, role=role)

    def _create_dynamodb_trigger_from_meta(self, lambda_name,
                                           trigger_meta,
                                           starting_position,
                                           role):
        validate_params(lambda_name, trigger_meta,
                        DYNAMODB_TRIGGER_REQUIRED_PARAMS)

        resource_ref = build_function_arn_ref(function_name=lambda_name)
        table_name = trigger_meta['target_table']
        table = self.template.get_resource_by_name(resource_name=table_name)
        if not table:
            raise AssertionError(f'Table {table_name} specified in '
                                 f'{lambda_name} trigger meta, but doesnt'
                                 f' exist in the lis of resources to deploy')
        if table['stream_enabled']:
            table.update({'stream_enabled': 'true',
                          'stream_view_type': 'NEW_AND_OLD_IMAGES'})

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     table_name)

        stream_arn = build_dynamo_db_stream_arn_ref(table_name=table_name)
        event_source = dynamodb_event_source(resource_name=trigger_name,
                                             starting_position=starting_position,
                                             function_arn_ref=resource_ref,
                                             table_stream_arn=stream_arn)
        self.template.add_aws_lambda_event_source_mapping(meta=event_source)

    def _create_cloud_watch_trigger_from_meta(self, lambda_name,
                                              trigger_meta,
                                              starting_position,
                                              role):
        validate_params(lambda_name, trigger_meta,
                        CLOUD_WATCH_TRIGGER_REQUIRED_PARAMS)

        target_rule = trigger_meta.get('target_rule')
        target_rule = f'{target_rule}_{self.config.region}'
        rule_ref = build_cloud_watch_event_rule_name_ref(
            target_rule=target_rule)

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     target_rule)

        resource_ref = build_function_arn_ref(function_name=lambda_name)
        event_source = cloud_watch_trigger(resource_name=trigger_name,
                                           rule_ref=rule_ref,
                                           resource_arn_ref=resource_ref)
        self.template.add_aws_cloudwatch_event_target(event_source)

    def _create_s3_trigger_from_meta(self, lambda_name,
                                     trigger_meta,
                                     starting_position,
                                     role):
        validate_params(lambda_name, trigger_meta,
                        S3_TRIGGER_REQUIRED_PARAMS)
        target_bucket = trigger_meta['target_bucket']
        events = trigger_meta['s3_events']

        lambda_permission_name = build_terraform_resource_name(target_bucket,
                                                               lambda_name,
                                                               'permission')
        lambda_permission = aws_lambda_permission(
            tf_resource_name=lambda_permission_name,
            function_name=lambda_name,
            bucket_name=target_bucket)
        self.template.add_aws_lambda_permission(meta=lambda_permission)

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     target_bucket)

        bucket_notification = aws_s3_bucket_notification(
            resource_name=trigger_name,
            bucket_name=target_bucket,
            lambda_function=lambda_name,
            events=events,
            lambda_permission=[lambda_permission_name])
        self.template.add_aws_s3_bucket_notification(meta=bucket_notification)

    def _create_sns_topic_trigger_from_meta(self, lambda_name,
                                            trigger_meta,
                                            starting_position,
                                            role):
        validate_params(lambda_name, trigger_meta, SNS_TRIGGER_REQUIRED_PARAMS)
        topic_name = trigger_meta['target_topic']

        lambda_name_ref = build_function_arn_ref(function_name=lambda_name)
        topic_arn_ref = build_sns_topic_arn_ref(sns_topic=topic_name)

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     topic_name)

        topic_subscription = aws_sns_topic_subscription(
            resource_name=trigger_name,
            topic_arn_ref=topic_arn_ref,
            protocol='lambda',
            endpoint=lambda_name_ref)
        self.template.add_aws_sns_topic_subscription(meta=topic_subscription)

    def _create_kinesis_stream_trigger_from_meta(self, lambda_name,
                                                 trigger_meta,
                                                 starting_position,
                                                 role):
        validate_params(lambda_name, trigger_meta,
                        KINESIS_TRIGGER_REQUIRED_PARAMS)
        stream_name = trigger_meta['target_stream']
        stream = self.template.get_resource_by_name(stream_name)
        if not stream:
            _LOG.error('Kinesis stream does not exist: {0}.'
                       .format(stream_name))
            return

        stream_arn = build_kinesis_stream_arn_ref(stream_name=stream_name)
        lambda_arn_ref = build_function_arn_ref(function_name=lambda_name)
        policy_name = '{0}KinesisTo{1}Lambda'.format(stream_name,
                                                     lambda_name)
        policy_document = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        lambda_arn_ref
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
        role_id_ref = build_role_id_ref(role_name=role)
        iam_role_policy = aws_iam_role_policy(policy_name=policy_name,
                                              policy_content=json.dumps(
                                                  policy_document),
                                              role_id_ref=role_id_ref)
        self.template.add_aws_iam_role_policy(meta=iam_role_policy)

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     stream_name)

        source_mapping = kinesis_source_mapping(resource_name=trigger_name,
                                                kinesis_stream_arn=stream_arn,
                                                lambda_arn_ref=lambda_arn_ref)
        self.template.add_aws_lambda_event_source_mapping(meta=source_mapping)

    def _create_sqs_trigger_from_meta(self, lambda_name, trigger_meta,
                                      starting_position, role):
        validate_params(lambda_name, trigger_meta,
                        SQS_TRIGGER_REQUIRED_PARAMS)
        target_queue = trigger_meta['target_queue']
        queue_arn_ref = build_sqs_queue_arn_ref(queue_name=target_queue)
        resource_ref = build_function_arn_ref(function_name=lambda_name)

        event_source_res_type = trigger_meta.get('resource_type')
        trigger_name = build_terraform_resource_name(lambda_name,
                                                     event_source_res_type,
                                                     target_queue)
        event_source = sqs_source_mapping(resource_name=trigger_name,
                                          sqs_queue_arn_ref=queue_arn_ref,
                                          function_name_ref=resource_ref)
        self.template.add_aws_lambda_event_source_mapping(meta=event_source)

    CREATE_TRIGGER = {
        'dynamodb_trigger': _create_dynamodb_trigger_from_meta,
        'cloudwatch_rule_trigger': _create_cloud_watch_trigger_from_meta,
        's3_trigger': _create_s3_trigger_from_meta,
        'sns_topic_trigger': _create_sns_topic_trigger_from_meta,
        'kinesis_trigger': _create_kinesis_stream_trigger_from_meta,
        'sqs_trigger': _create_sqs_trigger_from_meta
    }


def aws_s3_bucket_notification(resource_name, bucket_name, lambda_function,
                               events, lambda_permission):
    bucket_id_ref = build_bucket_id_ref(bucket_name=bucket_name)
    lambda_function_arn_ref = build_function_arn_ref(
        function_name=lambda_function)

    dependencies = []
    for permission in lambda_permission:
        dependencies.append(f'aws_lambda_permission.{permission}')

    resource = {
        resource_name: {
            'bucket': bucket_id_ref,
            'lambda_function': {
                'lambda_function_arn': lambda_function_arn_ref,
                'events': events
            },
            'depends_on': dependencies
        }
    }
    return resource


def aws_lambda_permission(tf_resource_name, function_name, bucket_name):
    function_arn_ref = build_function_arn_ref(function_name=function_name)
    bucket_arn_ref = build_bucket_arn_ref(bucket_name=bucket_name)
    resource = {
        tf_resource_name: {
            'function_name': function_arn_ref,
            'action': 'lambda:InvokeFunction',
            'principal': 's3.amazonaws.com',
            'source_arn': bucket_arn_ref,
            'statement_id': 'AllowExecutionFromS3Bucket'
        }
    }
    return resource


def aws_sns_topic_subscription(resource_name, topic_arn_ref, protocol,
                               endpoint):
    resource = {
        resource_name: {
            'topic_arn': topic_arn_ref,
            'protocol': protocol,
            'endpoint': endpoint
        }
    }
    return resource


def aws_iam_role_policy(policy_name, role_id_ref, policy_content):
    resource = {
        policy_name: {
            'name': policy_name,
            'role': role_id_ref,
            'policy': policy_content
        }
    }
    return resource


def aws_iam_role_policy_attachment(role_name, policy_arn_ref, role_name_ref):
    resource = {
        f'{role_name}_policy_attachment': {
            "policy_arn": policy_arn_ref,
            "role": role_name_ref
        }
    }
    return resource


def kinesis_source_mapping(resource_name, kinesis_stream_arn, lambda_arn_ref):
    resource = {
        resource_name: {
            "event_source_arn": kinesis_stream_arn,
            "function_name": lambda_arn_ref,
            "starting_position": "LATEST"
        }
    }
    return resource


def sqs_source_mapping(resource_name, sqs_queue_arn_ref, function_name_ref):
    resource = {
        resource_name: {
            "event_source_arn": sqs_queue_arn_ref,
            "function_name": function_name_ref
        }
    }
    return resource


def cloud_watch_trigger(resource_name, resource_arn_ref, rule_ref):
    resource = {
        resource_name:
            {
                "arn": resource_arn_ref,
                "rule": rule_ref
            }
    }
    return resource


def dynamodb_event_source(resource_name, table_stream_arn,
                          function_arn_ref, starting_position):
    resource = {
        resource_name: {
            "event_source_arn": table_stream_arn,
            "function_name": function_arn_ref,
            "starting_position": starting_position
        }
    }
    return resource


def cloud_watch_log_group(lambda_name, retention):
    name = get_lambda_log_group_name(lambda_name=lambda_name)
    resource = {
        "log": {
            "name": name,
            "retention_in_days": retention
        }
    }
    return resource


def provisioned_concurrency_config_with_lambda_version(name, function_name,
                                                       provisioned_concur):
    function_name_ref = build_function_name_ref(function_name=function_name)
    version_ref = build_lambda_version_ref(function_name=function_name)
    resource = {
        name: {
            "function_name": function_name_ref,
            "provisioned_concurrent_executions": provisioned_concur[
                'value'],
            "qualifier": version_ref
        }
    }
    return resource


def provisioned_concurrency_config_with_lambda_alias(name, function_name,
                                                     provisioned_concur,
                                                     alias_name):
    function_name_ref = build_function_name_ref(function_name=function_name)
    alias_name_ref = build_lambda_alias_name_ref(alias_name=alias_name)
    resource = {
        name: {
            "function_name": function_name_ref,
            "provisioned_concurrent_executions": provisioned_concur[
                'value'],
            "qualifier": alias_name_ref
        }
    }
    return resource


def template_for_alias(resource_name, alias_name, function_name):
    function_ref = build_function_arn_ref(function_name=function_name)
    function_version = build_lambda_version_ref(function_name=function_name)
    resource = {
        resource_name: {
            'name': alias_name,
            'function_name': function_ref,
            'function_version': function_version
        }
    }
    return resource


def template_for_lambda(lambda_name, role_arn, handler, runtime,
                        function_name, subnet_ids, security_group_ids,
                        s3_key=None,
                        s3_bucket=None,
                        memory=None,
                        timeout=None,
                        env_variables=None, layers=None, publish=False,
                        reserved_concurrent_executions=None,
                        tracing_mode=None, lambda_layers_arns=None):

    lambda_res = {
        'function_name': function_name,
        'role': role_arn,
        'runtime': runtime,
        'handler': handler,
        'publish': publish
    }

    if subnet_ids and security_group_ids:
        vpc_config = {
            'subnet_ids': subnet_ids,
            'security_group_ids': security_group_ids
        }
        lambda_res['vpc_config'] = vpc_config

    if s3_key and s3_bucket:
        lambda_res['s3_key'] = s3_key
        lambda_res['s3_bucket'] = s3_bucket
    if memory:
        lambda_res['memory_size'] = memory
    if timeout:
        lambda_res['timeout'] = timeout
    if env_variables:
        lambda_res['environment'] = [{'variables': env_variables}]
    if layers:
        lambda_res['layers'] = layers
    if reserved_concurrent_executions:
        lambda_res[
            'reserved_concurrent_executions'] = reserved_concurrent_executions
    if tracing_mode:
        lambda_res['tracing_config'] = {'mode': tracing_mode}
    if reserved_concurrent_executions:
        lambda_res[
            'reserved_concurrent_executions'] = reserved_concurrent_executions
    if lambda_layers_arns:
        lambda_res['layers'] = lambda_layers_arns

    resource = {lambda_name: lambda_res}
    return resource
