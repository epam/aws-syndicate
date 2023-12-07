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
from syndicate.core.conf.processor import ALL_REGIONS
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             check_region_available,
                                             create_args_for_multi_region,
                                             validate_params)

SNS_CLOUDWATCH_TRIGGER_REQUIRED_PARAMS = ['target_rule']

_LOG = get_logger('core.resources.sns_resource')


class SnsResource(BaseResource):

    def __init__(self, conn_provider, region) -> None:
        self.connection_provider = conn_provider
        self.region = region
        self.create_trigger = {
            'cloudwatch_rule_trigger':
                self._create_cloud_watch_trigger_from_meta
        }

    def describe_sns(self, name, meta, region, arn=None):
        if not arn:
            arn = self.connection_provider.sns(region).get_topic_arn(name)
        response = self.connection_provider.sns(region).get_topic_attributes(
            arn)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_sns_from_meta(self, name, meta):
        new_region_args = create_args_for_multi_region(
            [
                {
                    'name': name,
                    'meta': meta
                }
            ],
            ALL_REGIONS)
        responses = []
        for arg in new_region_args:
            region = arg['region']
            topic_arn = self.connection_provider.sns(region).get_topic_arn(
                name)
            if not topic_arn:
                continue
            response = self.connection_provider.sns(
                region).get_topic_attributes(
                topic_arn)
            if response:
                responses.append({'arn': topic_arn, 'response': response})
        description = []
        for topic in responses:
            description.append({
                topic['arn']: build_description_obj(
                    topic['response'], name, meta)
            })
        return description

    def describe_sns_application(self, name, meta, region, arn=None):
        if not arn:
            arn = self.connection_provider.sns(
                region).get_platform_application(name)
        response = self.connection_provider.sns(
            region).get_platform_application_attributes(arn)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_sns_application_from_meta(self, name, meta):
        new_region_args = create_args_for_multi_region(
            [
                {
                    'name': name,
                    'meta': meta
                }
            ],
            ALL_REGIONS)
        responses = []
        for arg in new_region_args:
            region = arg['region']
            app_arn = self.connection_provider.sns(
                region).get_platform_application(
                name)
            if not app_arn:
                continue
            response = self.connection_provider.sns(
                region).get_platform_application_attributes(
                app_arn)
            if response:
                responses.append({'arn': app_arn, 'response': response})
        description = []
        for topic in responses:
            description.append({
                topic['arn']: build_description_obj(
                    topic['response'], name, meta)
            })
        return description

    def create_sns_topic(self, args):
        """ Create sns topic from meta in region/regions.

        :type args: list
        """
        new_region_args = create_args_for_multi_region(args, ALL_REGIONS)
        return self.create_pool(self._create_sns_topic_from_meta,
                                new_region_args)

    def create_sns_application(self, args):
        """ Create sns application from meta in region/regions.

        :type args: list
        """
        new_region_args = create_args_for_multi_region(args, ALL_REGIONS)
        return self.create_pool(self._create_platform_application_from_meta,
                                new_region_args)

    @unpack_kwargs
    def _create_sns_topic_from_meta(self, name, meta, region):
        arn = self.connection_provider.sns(region).get_topic_arn(name)
        if arn:
            _LOG.warn(
                '{0} sns topic exists in region {1}.'.format(name, region))
            return self.describe_sns(name=name, meta=meta, region=region,
                                     arn=arn)
        arn = self.connection_provider.sns(region).create_topic(name)
        event_sources = meta.get('event_sources')
        if event_sources:
            for trigger_meta in event_sources:
                trigger_type = trigger_meta['resource_type']
                func = self.create_trigger[trigger_type]
                func(name, trigger_meta, region)
        _LOG.info('SNS topic %s in region %s created.', name, region)
        return self.describe_sns(name=name, meta=meta, region=region, arn=arn)

    def _subscribe_lambda_to_sns_topic(self, lambda_arn, topic_name, region):
        topic_arn = self.connection_provider.sns(region).subscribe(lambda_arn,
                                                                   topic_name,
                                                                   'lambda')
        try:
            self.connection_provider.lambda_conn().add_invocation_permission(
                lambda_arn,
                'sns.amazonaws.com',
                source_arn=topic_arn)
        except ClientError:
            _LOG.warn('The final access policy size for lambda {} is reached. '
                      'The limit is 20480 bytes. '
                      'Invocation permission was not added.'.format(
                lambda_arn))

    def create_sns_subscription_for_lambda(self, lambda_arn, topic_name,
                                           region):
        """ Create subscription for lambda on SNS topic in specified
        region/regions.

        :type lambda_arn: str
        :type topic_name: str
        :type region: str
        """
        if region:
            if isinstance(region, str):
                if region == 'all':
                    for each in ALL_REGIONS:
                        self._subscribe_lambda_to_sns_topic(lambda_arn,
                                                            topic_name,
                                                            each)
                else:
                    if check_region_available(region, ALL_REGIONS):
                        self._subscribe_lambda_to_sns_topic(lambda_arn,
                                                            topic_name,
                                                            region)
            elif isinstance(region, list):
                for each in region:
                    if check_region_available(each, ALL_REGIONS):
                        self._subscribe_lambda_to_sns_topic(lambda_arn,
                                                            topic_name,
                                                            each)
            else:
                raise AssertionError('Invalid value for SNS region: %s.',
                                     region)
        else:
            self._subscribe_lambda_to_sns_topic(lambda_arn, topic_name,
                                                self.region)

    def _create_cloud_watch_trigger_from_meta(self, topic_name, trigger_meta,
                                              region):
        required_parameters = SNS_CLOUDWATCH_TRIGGER_REQUIRED_PARAMS
        validate_params(topic_name, trigger_meta, required_parameters)
        rule_name = trigger_meta['target_rule']

        topic_arn = self.connection_provider.sns(region).get_topic_arn(
            topic_name)
        self.connection_provider.cw_events(region).add_rule_target(
            rule_name, topic_arn)
        self.connection_provider.sns(region).allow_service_invoke(
            topic_arn, 'events.amazonaws.com')
        _LOG.info('SNS topic %s subscribed to cloudwatch rule %s', topic_name,
                  rule_name)

    def remove_sns_topics(self, args):
        self.create_pool(self._remove_sns_topic, args)

    @unpack_kwargs
    def _remove_sns_topic(self, arn, config):
        region = arn.split(':')[3]
        topic_name = config['resource_name']
        # TODO delete remove_sns_topic_subscriptions when AWS will start
        #  deleting subscriptions with related SNS topic deletion
        self._remove_sns_topic_subscriptions(arn)
        try:
            self.connection_provider.sns(region).remove_topic_by_arn(arn)
            _LOG.info('SNS topic %s was removed.', topic_name)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'ResourceNotFoundException':
                _LOG.warn('SNS topic %s is not found', topic_name)
            else:
                raise e

    def _remove_sns_topic_subscriptions(self, topic_arn):
        region = topic_arn.split(':')[3]
        subscriptions = (self.connection_provider.sns(region).
                         list_subscriptions_by_topic(topic_arn))
        for subscription in subscriptions:
            subscription_arn = subscription['SubscriptionArn']
            self.connection_provider.sns(region).unsubscribe(
                    subscription_arn)

    @unpack_kwargs
    def _create_platform_application_from_meta(self, name, meta, region):
        required_parameters = ['platform', 'attributes']
        validate_params(name, meta, required_parameters)
        arn = self.connection_provider.sns(region).get_platform_application(
            name)
        if arn:
            _LOG.warn(
                '{0} SNS platform application exists in region {1}.'.format(
                    name, region))
            return self.describe_sns_application(name, meta, region, arn)
        platform = meta['platform']
        atrbts = meta['attributes']
        try:
            arn = self.connection_provider.sns(
                region).create_platform_application(
                name=name,
                platform=platform,
                attributes=atrbts)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'InvalidParameterException':
                _LOG.warn('SNS application %s is already exist.', name)
            else:
                raise e
        _LOG.info('SNS platform application %s in region %s has been created.',
                  name, region)
        return self.describe_sns_application(name, meta, region, arn)

    def remove_sns_application(self, args):
        self.create_pool(self._remove_sns_application, args)

    @unpack_kwargs
    def _remove_sns_application(self, arn, config):
        region = arn.split(':')[3]
        application_name = config['resource_name']
        try:
            self.connection_provider.sns(region).remove_application_by_arn(arn)
            _LOG.info('SNS application %s was removed.', application_name)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'ResourceNotFoundException':
                _LOG.warn('SNS application %s is not found', application_name)
            else:
                raise e
