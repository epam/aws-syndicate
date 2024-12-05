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

    def __init__(self, cw_conn, sns_conn, lambda_conn,
                 lambda_res, account_id) -> None:
        self.client = cw_conn
        self.sns_conn = sns_conn
        self.lambda_conn = lambda_conn
        self.lambda_res = lambda_res
        self.account_id = account_id

    def create_alarm(self, args):
        """ Create alarm in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_alarm_from_meta, args)

    def describe_alarm(self, name, meta):
        response = self.client.describe_alarms([name])
        if not response:
            return {}
        arn = response[0]['AlarmArn']
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
            _LOG.warning(f'{name} alarm exists.')
            return self.describe_alarm(name, meta)

        params = dict(alarm_name=name, metric_name=meta['metric_name'],
                      namespace=meta['namespace'], period=meta['period'],
                      evaluation_periods=meta['evaluation_periods'],
                      threshold=meta['threshold'], statistic=meta['statistic'],
                      comparison_operator=meta['comparison_operator'],
                      description=meta.get('description'),
                      dimensions=meta.get('dimensions'),
                      datapoints=meta.get('datapoints'), alarm_actions=[],
                      evaluate_low_sample_count_percentile=meta.get(
                          'evaluate_low_sample_count_percentile'),
                      tags=meta.get('tags'))

        if sns_topics := meta.get('sns_topics'):
            for each in sns_topics:
                if arn := self.sns_conn.get_topic_arn(each):
                    params['alarm_actions'].append(arn)
        if lambdas := meta.get('lambdas'):
            for each in lambdas:
                arn = self.lambda_res.build_lambda_arn(each)
                if self.lambda_conn.get_function(arn):
                    params['alarm_actions'].append(arn)
        if response_plans := meta.get('ssm_response_plan'):
            for each in response_plans:
                params['alarm_actions'].append(
                    f'arn:aws:ssm-incidents::{self.account_id}:responseplan/{each}')

        self.client.put_metric_alarm(**params)
        _LOG.info(f'Created alarm {name}.')
        return self.describe_alarm(name, meta)

    def remove_alarms(self, args):
        return self._remove_alarms(args)

    def _remove_alarms(self, args):
        results = {}
        errors = []
        for param_chunk in chunks(args, 100):
            alarm_names = [x['config']['resource_name'] for x in param_chunk]
            try:
                self.client.remove_alarms(alarm_names=alarm_names,
                                          log_not_found_error=False)
                _LOG.info('Alarms %s were removed.', str(alarm_names))
                results.update({x['arn']: x['config'] for x in param_chunk})

            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    _LOG.warn('Alarms %s are not found', str(alarm_names))
                else:
                    errors.append(str(e))
                described_alarms = self.client.alarm_list(alarm_names)
                described_alarm_names = [x['AlarmName'] for x in
                                         described_alarms]
                results.update(
                    {x['arn']: x['config'] for x in param_chunk
                     if x['config']['resource_name'] not in
                     described_alarm_names})

        return (results, errors) if errors else results
