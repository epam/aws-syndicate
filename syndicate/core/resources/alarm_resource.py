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

from syndicate.commons.log_helper import get_logger
from syndicate.core import CONN
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.helper import (build_description_obj, chunks,
                                             validate_params)

_LOG = get_logger('syndicate.core.resources.alarm_resource')
_CW_METRIC = CONN.cw_metric()


def create_alarm(args):
    """ Create alarm in pool in sub processes.

    :type args: list
    """
    return create_pool(_create_alarm_from_meta, args, 5)


def describe_alarm(name, meta):
    response = _CW_METRIC.describe_alarms([name])[0]
    arn = response['AlarmArn']
    return {
        arn: build_description_obj(response, name, meta)
    }


@unpack_kwargs
def _create_alarm_from_meta(name, meta):
    """ Create alarm resource in AWS Cloud via meta description.

    :type name: str
    :type meta: dict
    """
    required_parameters = ['metric_name', 'namespace', 'period', 'threshold',
                           'evaluation_periods', 'comparison_operator',
                           'statistic']
    validate_params(name, meta, required_parameters)

    if _CW_METRIC.is_alarm_exists(name):
        _LOG.warn('%s alarm exists.', name)
        return describe_alarm(name, meta)

    params = dict(alarm_name=name, metric_name=meta['metric_name'],
                  namespace=meta['namespace'], period=meta['period'],
                  evaluation_periods=meta['evaluation_periods'],
                  threshold=meta['threshold'], statistic=meta['statistic'],
                  comparison_operator=meta['comparison_operator'])

    sns_topics = meta.get('sns_topics')
    sns_topic_arns = []
    if sns_topics:
        for each in sns_topics:
            arn = CONN.sns().get_topic_arn(each)
            sns_topic_arns.append(arn)
        if sns_topic_arns:
            params['alarm_actions'] = sns_topic_arns

    _CW_METRIC.put_metric_alarm(**params)
    _LOG.info('Created alarm {0}.'.format(name))
    return describe_alarm(name, meta)


def remove_alarms(args):
    create_pool(remove_alarm_list, chunks(args, 100), 5)


def remove_alarm_list(*alarm_list):
    alarm_names = map(lambda x: x['config']['resource_name'], alarm_list[0])
    try:
        _CW_METRIC.remove_alarms(alarm_names=alarm_names)
        _LOG.info('Alarms %s were removed.', str(alarm_names))
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            _LOG.warn('Alarms %s are not found', str(alarm_names))
        else:
            raise e
