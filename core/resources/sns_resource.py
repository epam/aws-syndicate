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
from botocore.exceptions import ClientError

from commons.log_helper import get_logger
from core import CONN, CREDENTIALS
from core.conf.config_holder import ALL_REGIONS
from core.helper import create_pool, unpack_kwargs
from core.resources.helper import (build_description_obj,
                                   check_region_available,
                                   create_args_for_multi_region,
                                   validate_params)

_LOG = get_logger('core.resources.sns_resource')


def _describe_sns(arn, name, meta, region):
    response = CONN.sns(region).get_topic_attributes(arn)
    return {
        arn: build_description_obj(response, name, meta)
    }


def _describe_sns_application(arn, name, meta, region):
    response = CONN.sns(region).get_platform_application_attributes(arn)
    return {
        arn: build_description_obj(response, name, meta)
    }


def create_sns_topic(args):
    """ Create sns topic from meta in region/regions.

    :type args: list
    """
    new_region_args = create_args_for_multi_region(args, ALL_REGIONS)
    return create_pool(_create_sns_topic_from_meta, 1, new_region_args)


def create_sns_application(args):
    """ Create sns application from meta in region/regions.

    :type args: list
    """
    new_region_args = create_args_for_multi_region(args, ALL_REGIONS)
    return create_pool(_create_platform_application_from_meta, 1,
                       new_region_args)


@unpack_kwargs
def _create_sns_topic_from_meta(name, meta, region):
    arn = CONN.sns(region).get_topic_arn(name)
    if arn:
        _LOG.warn('{0} sns topic exists in region {1}.'.format(name, region))
        return _describe_sns(arn, name, meta, region)
    arn = CONN.sns(region).create_topic(name)
    event_sources = meta.get('event_sources')
    if event_sources:
        for trigger_meta in event_sources:
            trigger_type = trigger_meta['resource_type']
            func = CREATE_TRIGGER[trigger_type]
            func(name, trigger_meta, region)
    _LOG.info('SNS topic %s in region %s created.', name, region)
    return _describe_sns(arn, name, meta, region)


def _subscribe_lambda_to_sns_topic(lambda_arn, topic_name, region):
    topic_arn = CONN.sns(region).subscribe(lambda_arn, topic_name, 'lambda')
    lambda_name = lambda_arn.split(':')[-1]
    CONN.lambda_conn().add_invocation_permission(lambda_name,
                                                 'sns.amazonaws.com',
                                                 source_arn=topic_arn)


def create_sns_subscription_for_lambda(lambda_arn, topic_name, region):
    """ Create subscription for lambda on SNS topic in specified
    region/regions.

    :type lambda_arn: str
    :type topic_name: str
    :type region: str
    """
    if region:
        if isinstance(region, str) or isinstance(region, unicode):
            if region == 'all':
                for each in ALL_REGIONS:
                    _subscribe_lambda_to_sns_topic(lambda_arn, topic_name,
                                                   each)
            else:
                if check_region_available(region, ALL_REGIONS):
                    _subscribe_lambda_to_sns_topic(lambda_arn, topic_name,
                                                   region)
        elif isinstance(region, list):
            for each in region:
                if check_region_available(each, ALL_REGIONS):
                    _subscribe_lambda_to_sns_topic(lambda_arn, topic_name,
                                                   each)
        else:
            raise AssertionError('Invalid value for SNS region: %s.', region)
    else:
        _subscribe_lambda_to_sns_topic(lambda_arn, topic_name,
                                       CREDENTIALS['region'])


def _create_cloud_watch_trigger_from_meta(topic_name, trigger_meta, region):
    required_parameters = ['target_rule']
    validate_params(topic_name, trigger_meta, required_parameters)
    rule_name = trigger_meta['target_rule']

    topic_arn = CONN.sns(region).get_topic_arn(topic_name)
    CONN.cw_events(region).add_rule_target(rule_name, topic_arn)
    CONN.sns(region).allow_service_invoke(topic_arn, 'events.amazonaws.com')
    _LOG.info('SNS topic %s subscribed to cloudwatch rule %s', topic_name,
              rule_name)


CREATE_TRIGGER = {
    'cloudwatch_rule_trigger': _create_cloud_watch_trigger_from_meta
}


def remove_sns_topics(args):
    create_pool(_remove_sns_topic, 1, args)


@unpack_kwargs
def _remove_sns_topic(arn, config):
    region = arn.split(':')[3]
    topic_name = config['resource_name']
    try:
        CONN.sns(region).remove_topic_by_arn(arn)
        _LOG.info('SNS topic %s was removed.', topic_name)
    except ClientError as e:
        exception_type = e.response['Error']['Code']
        if exception_type == 'ResourceNotFoundException':
            _LOG.warn('SNS topic %s is not found', topic_name)
        else:
            raise e


@unpack_kwargs
def _create_platform_application_from_meta(name, meta, region=None):
    arn = CONN.sns(region).get_platform_application(name)
    if arn:
        _LOG.warn('{0} SNS platform application exists in region {1}.'.format(
            name, region))
        return _describe_sns_application(arn, name, meta, region)
    platform = meta.get('platform')
    attributes = meta.get('attributes')
    try:
        arn = CONN.sns(region).create_platform_application(
            name=name, platform=platform, attributes=attributes)
    except ClientError as e:
        exception_type = e.response['Error']['Code']
        if exception_type == 'InvalidParameterException':
            _LOG.warn('SNS application %s is already existed.', name)
        else:
            raise e
    _LOG.info('SNS platform application %s in region %s has been created.',
              name, region)
    return _describe_sns_application(arn, name, meta, region)


def remove_sns_application(args):
    create_pool(_remove_sns_application, 1, args)


@unpack_kwargs
def _remove_sns_application(arn, config):
    region = arn.split(':')[3]
    application_name = config['resource_name']
    try:
        CONN.sns(region).remove_application_by_arn(arn)
        _LOG.info('SNS application %s was removed.', application_name)
    except ClientError as e:
        exception_type = e.response['Error']['Code']
        if exception_type == 'ResourceNotFoundException':
            _LOG.warn('SNS application %s is not found', application_name)
        else:
            raise e
