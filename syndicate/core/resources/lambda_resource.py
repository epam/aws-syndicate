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
import time

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import retry
from syndicate.core import CONFIG, CONN
from syndicate.core.build.meta_processor import S3_PATH_NAME
from syndicate.core.helper import (create_pool, unpack_kwargs)
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
from syndicate.core.resources.sns_resource import (
    create_sns_subscription_for_lambda)

_LOG = get_logger('syndicate.core.resources.lambda_resource')
_LAMBDA_CONN = CONN.lambda_conn()
_S3_CONN = CONN.s3()
_CW_LOGS_CONN = CONN.cw_logs()


def create_lambda(args):
    """ Create lambdas in pool in sub processes.

    :type args: list
    """
    return create_pool(_create_lambda_from_meta, args)


def update_lambda(args):
    return create_pool(_update_lambda, args)


def describe_lambda(name, meta, response=None):
    if not response:
        response = _LAMBDA_CONN.get_function(lambda_name=name)
    arn = build_lambda_arn_with_alias(response, meta.get('alias'))

    del response['Configuration']['FunctionArn']
    return {
        arn: build_description_obj(response, name, meta)
    }


def build_lambda_arn(name):
    arn = 'arn:aws:lambda:{0}:{1}:function:{2}'.format(CONFIG.region,
                                                       CONFIG.account_id, name)
    return arn


def resolve_lambda_arn_by_version_and_alias(name, version, alias):
    if version or alias:
        lambda_response = _LAMBDA_CONN.get_function(name, version)
        return build_lambda_arn_with_alias(lambda_response, alias)
    else:
        return _LAMBDA_CONN.get_function(name)['Configuration']['FunctionArn']


def build_lambda_arn_with_alias(response, alias=None):
    name = response['Configuration']['FunctionName']
    l_arn = build_lambda_arn(name=name)
    version = response['Configuration']['Version']
    arn = '{0}:{1}'.format(l_arn, version)
    # override version if alias exists
    if alias:
        arn = '{0}:{1}'.format(l_arn, alias)
    return arn


@unpack_kwargs
def _create_lambda_from_meta(name, meta):
    req_params = ['iam_role_name', 'runtime', 'memory', 'timeout', 'func_name']

    # Lambda configuration
    validate_params(name, meta, req_params)

    key = meta[S3_PATH_NAME]
    if not _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        raise AssertionError('Deployment package %s does not exist '
                             'in %s bucket', key, CONFIG.deploy_target_bucket)

    response = _LAMBDA_CONN.get_function(name)
    if response:
        _LOG.warn('%s lambda exists.', name)
        return describe_lambda(name, meta, response)

    role_name = meta['iam_role_name']
    role_arn = CONN.iam().check_if_role_exists(role_name)
    if not role_arn:
        raise AssertionError('Role {0} does not exist.'.format(role_name))

    dl_type = meta.get('dl_resource_type')
    if dl_type:
        dl_type = dl_type.lower()
    dl_name = meta.get('dl_resource_name')

    dl_target_arn = 'arn:aws:{0}:{1}:{2}:{3}'.format(dl_type,
                                                     CONFIG.region,
                                                     CONFIG.account_id,
                                                     dl_name) if dl_type and dl_name else None

    publish_version = meta.get('publish_version', False)

    _LAMBDA_CONN.create_lambda(
        lambda_name=name,
        func_name=meta['func_name'],
        role=role_arn,
        runtime=meta['runtime'].lower(),
        memory=meta['memory'],
        timeout=meta['timeout'],
        s3_bucket=CONFIG.deploy_target_bucket,
        s3_key=key,
        env_vars=meta.get('env_variables'),
        vpc_sub_nets=meta.get('subnet_ids'),
        vpc_security_group=meta.get('security_group_ids'),
        dl_target_arn=dl_target_arn,
        tracing_mode=meta.get('tracing_mode'),
        publish_version=publish_version
    )

    # AWS sometimes returns None after function creation, needs for stability
    time.sleep(10)
    response = __describe_lambda_by_version(
        name) if publish_version else _LAMBDA_CONN.get_function(name)
    version = response['Configuration']['Version']
    con_exec = meta.get('concurrent_executions')
    if con_exec:
        _LOG.debug('Going to set up concurrency executions')
        unresolved_exec = _LAMBDA_CONN.get_unresolved_concurrent_executions()
        if con_exec <= unresolved_exec:
            _LAMBDA_CONN.put_function_concurrency(
                function_name=name,
                concurrent_executions=con_exec)
            _LOG.debug('Concurrency is enabled for %s lambda', name)
        else:
            _LOG.warn(
                'Account does not have any unresolved executions.'
                ' Current size - %s', unresolved_exec)

    # enabling aliases
    # aliases can be enabled only and for $LATEST
    alias = meta.get('alias')
    if alias:
        _LOG.debug('Creating alias')
        _LOG.debug(_LAMBDA_CONN.create_alias(function_name=name,
                                             name=alias, version=version))

    arn = build_lambda_arn_with_alias(response,
                                      alias) if publish_version or alias else \
        response['Configuration']['FunctionArn']
    _LOG.debug('arn value: ' + str(arn))

    if meta.get('event_sources'):
        for trigger_meta in meta.get('event_sources'):
            trigger_type = trigger_meta['resource_type']
            func = CREATE_TRIGGER[trigger_type]
            func(name, arn, role_name, trigger_meta)
    _LOG.info('Created lambda %s.', name)
    return describe_lambda(name, meta, response)


@unpack_kwargs
def _update_lambda(name, meta):
    _LOG.info('Updating lambda: {0}'.format(name))
    req_params = ['runtime', 'memory', 'timeout', 'func_name']

    validate_params(name, meta, req_params)

    key = meta[S3_PATH_NAME]
    if not _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        raise AssertionError(
            'Deployment package {0} does not exist '
            'in {1} bucket'.format(key, CONFIG.deploy_target_bucket))

    response = _LAMBDA_CONN.get_function(name)
    if not response:
        raise AssertionError('{0} lambda does not exist.'.format(name))

    publish_version = meta.get('publish_version', False)

    _LAMBDA_CONN.update_code_source(
        lambda_name=name,
        s3_bucket=CONFIG.deploy_target_bucket,
        s3_key=key,
        publish_version=publish_version)

    # AWS sometimes returns None after function creation, needs for stability
    time.sleep(10)
    response = _LAMBDA_CONN.get_function(name)
    _LOG.debug('Lambda describe result: {0}'.format(response))
    code_sha_256 = response['Configuration']['CodeSha256']
    publish_ver_response = _LAMBDA_CONN.publish_version(
        function_name=name,
        code_sha_256=code_sha_256)
    updated_version = publish_ver_response['Version']
    _LOG.info(
        'Version {0} for lambda {1} published'.format(updated_version, name))

    alias_name = meta.get('alias')
    if alias_name:
        alias = _LAMBDA_CONN.get_alias(function_name=name, name=alias_name)
        if not alias:
            _LAMBDA_CONN.create_alias(
                function_name=name,
                name=alias_name,
                version=updated_version)
            _LOG.info(
                'Alias {0} has been created for lambda {1}'.format(alias_name,
                                                                   name))
        else:
            _LAMBDA_CONN.update_alias(
                function_name=name,
                alias_name=alias_name,
                function_version=updated_version)
            _LOG.info(
                'Alias {0} has been updated for lambda {1}'.format(alias_name,
                                                                   name))


def __describe_lambda_by_version(name):
    versions = _LAMBDA_CONN.versions_list(name)
    # find the last created version
    version = max(
        [int(i['Version']) if i['Version'] != '$LATEST' else 0 for i in
         versions])
    if version != 0:
        return _LAMBDA_CONN.get_function(name, str(version))
    else:
        return _LAMBDA_CONN.get_function(name)


@retry
def _create_dynamodb_trigger_from_meta(lambda_name, lambda_arn, role_name,
                                       trigger_meta):
    required_parameters = ['target_table', 'batch_size']
    validate_params(lambda_name, trigger_meta, required_parameters)
    table_name = trigger_meta['target_table']

    if not CONN.dynamodb().is_stream_enabled(table_name):
        CONN.dynamodb().enable_table_stream(table_name)

    stream = CONN.dynamodb().get_table_stream_arn(table_name)
    # TODO support another sub type
    _LAMBDA_CONN.add_event_source(lambda_arn, stream,
                                  trigger_meta['batch_size'],
                                  start_position='LATEST')
    # start_position='LATEST' - in case we did not remove tables before
    _LOG.info('Lambda %s subscribed to dynamodb table %s', lambda_name,
              table_name)


@retry
def _create_sqs_trigger_from_meta(lambda_name, lambda_arn, role_name,
                                  trigger_meta):
    required_parameters = ['target_queue', 'batch_size']
    validate_params(lambda_name, trigger_meta, required_parameters)
    target_queue = trigger_meta['target_queue']

    if not CONN.sqs().get_queue_url(target_queue, CONFIG.account_id):
        _LOG.debug('Queue %s does not exist', target_queue)
        return

    queue_arn = 'arn:aws:sqs:{0}:{1}:{2}'.format(CONFIG.region,
                                                 CONFIG.account_id,
                                                 target_queue)

    _LAMBDA_CONN.add_event_source(lambda_arn, queue_arn,
                                  trigger_meta['batch_size'])
    _LOG.info('Lambda %s subscribed to SQS queue %s', lambda_name,
              target_queue)


@retry
def _create_cloud_watch_trigger_from_meta(lambda_name, lambda_arn, role_name,
                                          trigger_meta):
    required_parameters = ['target_rule']
    validate_params(lambda_name, trigger_meta, required_parameters)
    rule_name = trigger_meta['target_rule']

    rule_arn = CONN.cw_events().get_rule_arn(rule_name)
    CONN.cw_events().add_rule_target(rule_name, lambda_arn)
    _LAMBDA_CONN.add_invocation_permission(lambda_arn, 'events.amazonaws.com',
                                           rule_arn)
    _LOG.info('Lambda %s subscribed to cloudwatch rule %s', lambda_name,
              rule_name)


@retry
def _create_s3_trigger_from_meta(lambda_name, lambda_arn, role_name,
                                 trigger_meta):
    required_parameters = ['target_bucket', 's3_events']
    validate_params(lambda_name, trigger_meta, required_parameters)
    target_bucket = trigger_meta['target_bucket']

    if not _S3_CONN.is_bucket_exists(target_bucket):
        _LOG.error(
            'S3 bucket {0} event source for lambda {1} was not created.'.format(
                target_bucket, lambda_name))
        return
    _LAMBDA_CONN.add_invocation_permission(lambda_arn,
                                           's3.amazonaws.com',
                                           'arn:aws:s3:::{0}'.format(
                                               target_bucket))
    _S3_CONN.configure_event_source_for_lambda(target_bucket, lambda_arn,
                                               trigger_meta['s3_events'])
    _LOG.info('Lambda %s subscribed to S3 bucket %s', lambda_name,
              target_bucket)


@retry
def _create_sns_topic_trigger_from_meta(lambda_name, lambda_arn, role_name,
                                        trigger_meta):
    required_params = ['target_topic']
    validate_params(lambda_name, trigger_meta, required_params)
    topic_name = trigger_meta['target_topic']

    region = trigger_meta.get('region')
    create_sns_subscription_for_lambda(lambda_arn, topic_name, region)
    _LOG.info('Lambda %s subscribed to sns topic %s', lambda_name,
              trigger_meta['target_topic'])


@retry
def _create_kinesis_stream_trigger_from_meta(lambda_name, lambda_arn,
                                             role_name, trigger_meta):
    required_parameters = ['target_stream', 'batch_size', 'starting_position']
    validate_params(lambda_name, trigger_meta, required_parameters)

    stream_name = trigger_meta['target_stream']

    stream = CONN.kinesis().get_stream(stream_name)
    stream_arn = stream['StreamDescription']['StreamARN']
    stream_status = stream['StreamDescription']['StreamStatus']
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
    CONN.iam().attach_inline_policy(role_name=role_name,
                                    policy_name=policy_name,
                                    policy_document=policy_document)
    _LOG.debug('Inline policy %s is attached to role %s',
               policy_name, role_name)
    _LOG.debug('Waiting for activation policy %s...', policy_name)
    time.sleep(10)

    _add_kinesis_event_source(lambda_arn, stream_arn, trigger_meta)
    _LOG.info('Lambda %s subscribed to kinesis stream %s', lambda_name,
              stream_name)


@retry
def _add_kinesis_event_source(lambda_name, stream_arn, trigger_meta):
    _LAMBDA_CONN.add_event_source(lambda_name, stream_arn,
                                  trigger_meta['batch_size'],
                                  trigger_meta['starting_position'])


CREATE_TRIGGER = {
    'dynamodb_trigger': _create_dynamodb_trigger_from_meta,
    'cloudwatch_rule_trigger': _create_cloud_watch_trigger_from_meta,
    's3_trigger': _create_s3_trigger_from_meta,
    'sns_topic_trigger': _create_sns_topic_trigger_from_meta,
    'kinesis_trigger': _create_kinesis_stream_trigger_from_meta,
    'sqs_trigger': _create_sqs_trigger_from_meta
}


def remove_lambdas(args):
    create_pool(_remove_lambda, args)


@unpack_kwargs
@retry
def _remove_lambda(arn, config):
    lambda_name = config['resource_name']
    try:
        _LAMBDA_CONN.delete_lambda(lambda_name)
        _LAMBDA_CONN.remove_trigger(lambda_name)
        group_names = _CW_LOGS_CONN.get_log_group_names()
        for each in group_names:
            if lambda_name == each.split('/')[-1]:
                _CW_LOGS_CONN.delete_log_group_name(each)
        _LOG.info('Lambda %s was removed.', lambda_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            _LOG.warn('Lambda %s is not found', lambda_name)
        else:
            raise e
