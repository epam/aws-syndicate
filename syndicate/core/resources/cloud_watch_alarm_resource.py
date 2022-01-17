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
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj, chunks,
                                             validate_params)

CLOUDWATCH_ALARM_REQUIRED_PARAMS = ['metric_name', 'namespace', 'period',
                                    'threshold', 'evaluation_periods',
                                    'comparison_operator', 'statistic']

_LOG = get_logger('syndicate.core.resources.alarm_resource')


class CloudWatchAlarmResource(BaseResource):

    def __init__(self, cw_conn, sns_conn) -> None:
        self.client = cw_conn
        self.sns_conn = sns_conn

    def create_alarm(self, args):
        """ Create alarm in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_alarm_from_meta, args)

    def describe_alarm(self, name, meta):
        response = self.client.describe_alarms([name])[0]
        arn = response['AlarmArn']
        return {
            arn: build_description_obj(response, name, meta)
        }

    @unpack_kwargs
    def _create_alarm_from_meta(self, name, meta):
        """ Create alarm resource in AWS Cloud via meta description.

        :type name: str
        :type meta: dict
        """
        validate_params(name, meta, CLOUDWATCH_ALARM_REQUIRED_PARAMS)

        if self.client.is_alarm_exists(name):
            _LOG.warn('%s alarm exists.', name)
            return self.describe_alarm(name, meta)

        params = dict(alarm_name=name, metric_name=meta['metric_name'],
                      namespace=meta['namespace'], period=meta['period'],
                      evaluation_periods=meta['evaluation_periods'],
                      threshold=meta['threshold'], statistic=meta['statistic'],
                      comparison_operator=meta['comparison_operator'])

        sns_topics = meta.get('sns_topics')
        sns_topic_arns = []
        if sns_topics:
            for each in sns_topics:
                arn = self.sns_conn.get_topic_arn(each)
                sns_topic_arns.append(arn)
            if sns_topic_arns:
                params['alarm_actions'] = sns_topic_arns

        self.client.put_metric_alarm(**params)
        _LOG.info('Created alarm {0}.'.format(name))
        return self.describe_alarm(name, meta)

    def remove_alarms(self, args):
        for param_chunk in chunks(args, 100):
            self.remove_alarm_list(param_chunk)

    def remove_alarm_list(self, alarm_list):
        alarm_names = [x['config']['resource_name'] for x in alarm_list]
        try:
            self.client.remove_alarms(alarm_names=alarm_names)
            _LOG.info('Alarms %s were removed.', str(alarm_names))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn('Alarms %s are not found', str(alarm_names))
            else:
                raise e
