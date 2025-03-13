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

from syndicate.exceptions import InvalidValueError, \
    ResourceNotFoundError
from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

CLOUDWATCH_ALARM_REQUIRED_PARAMS = ['metric_name', 'namespace', 'period',
                                    'threshold', 'evaluation_periods',
                                    'comparison_operator', 'statistic']

_LOG = get_logger(__name__)


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
                if arn := self._validate_lambda_resource(each):
                    params['alarm_actions'].append(arn)
        if response_plans := meta.get('ssm_response_plan'):
            for each in response_plans:
                params['alarm_actions'].append(
                    f'arn:aws:ssm-incidents::{self.account_id}:responseplan/{each}')

        self.client.put_metric_alarm(**params)
        _LOG.info(f'Created alarm {name}.')
        return self.describe_alarm(name, meta)

    def remove_alarms(self, args):
        return self.create_pool(self._remove_alarms, args)

    @unpack_kwargs
    def _remove_alarms(self, arn, config):
        alarm_name = config['resource_name']
        try:
            self.client.remove_alarms(alarm_names=[alarm_name],
                                      log_not_found_error=False)
            _LOG.info(f'Alarm {alarm_name} was removed.')

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn(f'Alarm {alarm_name} not found.')
            else:
                raise e
            described_alarms = self.client.alarm_list(alarm_names=[alarm_name])
            if described_alarms and any(alarm['AlarmName'] == alarm_name
                                        for alarm in described_alarms):
                _LOG.warn(f'Alarm {alarm_name} was found despite the '
                          f'`ResourceNotFoundException` error.')
                raise e

        return {arn: config}

    def _validate_lambda_resource(self, resource: str) -> str | None:
        from syndicate.core import CONFIG
        qualifier = None
        if ':' in resource:
            if resource.count(':') > 1:
                raise InvalidValueError(
                    f'Invalid lambda qualifier \'{resource}\''
                )

            resource_name, qualifier = resource.split(':')
            resource = f'{CONFIG.resources_prefix}{resource_name}' \
                       f'{CONFIG.resources_suffix}'

        arn = self.lambda_res.build_lambda_arn(resource)
        if self.lambda_conn.get_function(arn, qualifier):
            return arn
        else:
            raise ResourceNotFoundError(
                f'Cannot find lambda with arn \'{arn}\' '
                f'and qualifier \'{qualifier}\''
            )
