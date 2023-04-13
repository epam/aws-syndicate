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
from troposphere import cloudwatch

from syndicate.core.resources.cloud_watch_alarm_resource import \
    CLOUDWATCH_ALARM_REQUIRED_PARAMS
from syndicate.core.resources.helper import validate_params
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, sns_topic_logic_name


class CfCloudWatchAlarmConverter(CfResourceConverter):

    def convert(self, name, meta):
        validate_params(name, meta, CLOUDWATCH_ALARM_REQUIRED_PARAMS)

        alarm = cloudwatch.Alarm(to_logic_name('CloudWatchAlarm', name))

        alarm.AlarmName = name
        alarm.ComparisonOperator = meta['comparison_operator']
        alarm.EvaluationPeriods = meta['evaluation_periods']
        alarm.MetricName = meta['metric_name']
        alarm.Namespace = meta['namespace']
        alarm.Period = meta['period']
        alarm.Statistic = meta['statistic']
        alarm.Threshold = meta['threshold']

        sns_topics = meta.get('sns_topics')
        if sns_topics:
            sns_topic_arns = []
            for each in sns_topics:
                topic = self.get_resource(sns_topic_logic_name(each))
                sns_topic_arns.append(topic.ref())
                alarm.AlarmActions = sns_topic_arns

        self.template.add_resource(alarm)
