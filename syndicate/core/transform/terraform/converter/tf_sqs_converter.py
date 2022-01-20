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

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_helper import deploy_regions
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_sqs_queue_id_ref

FIFO_REGIONS = ['us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1']
FIFO_SUFFIX = '.fifo'


class SQSQueueConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        regions = deploy_regions(resource_name=name, meta=resource)
        default_region = self.config.region
        for region in regions:
            provider = None
            tf_resource_name = name
            if region != default_region:
                self.template.add_provider_if_not_exists(region=region)
                provider_type = self.template.provider_type()
                provider = f'{provider_type}.{region}'
                tf_resource_name = build_terraform_resource_name(name, region)

            fifo_queue = resource.get('fifo_queue')
            queue_name = self.build_resource_name(is_fifo=fifo_queue,
                                                  name=name)
            if fifo_queue and region not in FIFO_REGIONS:
                raise AssertionError('FIFO queue is not available in {0}.'
                                     .format(region))

            self.create_sqs_queue_in_region(name=queue_name,
                                            resource=resource,
                                            tf_queue_name=tf_resource_name,
                                            provider=provider,
                                            region=region,
                                            fifo_queue=fifo_queue)

    def create_sqs_queue_in_region(self, name, resource,
                                   tf_queue_name, fifo_queue, region=None,
                                   provider=None):
        vis_timeout = resource.get('visibility_timeout')
        if vis_timeout:
            if vis_timeout < 0 or vis_timeout > 43200:
                raise AssertionError(
                    'Visibility timeout must be '
                    'between 0 and 43200 seconds')
        delay_seconds = resource.get('delay_seconds')
        if delay_seconds:
            if delay_seconds < 0 or delay_seconds > 900:
                raise AssertionError(
                    'Delay seconds for queue must be '
                    'between 0 and 900 seconds')

        maximum_message_size = resource.get('maximum_message_size')
        if maximum_message_size:
            if maximum_message_size < 1024 or maximum_message_size > 262144:
                raise AssertionError(
                    'Maximum message size must be '
                    'between 1024 and 262144 bytes')

        message_retention_period = resource.get('message_retention_period')
        if message_retention_period:
            if message_retention_period < 60 or message_retention_period > 1209600:
                raise AssertionError(
                    'Message retention size must be '
                    'between 60 and 1209600 seconds')

        receive_mes_wait_sec = resource.get(
            'receive_message_wait_time_seconds')
        if receive_mes_wait_sec:
            if receive_mes_wait_sec < 0 or receive_mes_wait_sec > 20:
                raise AssertionError(
                    'Receive message wait time must be '
                    'between 0 and 20 seconds')

        content_based_deduplication = resource.get(
            'content_based_deduplication')
        redrive_policy = resource.get('redrive_policy')
        policy = resource.get('policy')
        if policy:
            if not policy.get('Version'):
                policy['Version'] = '2008-10-17'
            policy = json.dumps(policy)

        kms_master_key_id = resource.get('kms_master_key_id')
        kms_data_reuse_period = resource.get(
            'kms_data_key_reuse_period_seconds')
        if kms_data_reuse_period:
            if kms_data_reuse_period < 60 or kms_data_reuse_period > 86400:
                raise AssertionError(
                    'KMS key reuse period must be '
                    'between 60 and 86400 seconds')

        queue = self._sqs_queue(tf_queue_name=tf_queue_name, queue_name=name,
                                redrive_policy=redrive_policy,
                                delay_seconds=delay_seconds,
                                receive_wait_time_seconds=receive_mes_wait_sec,
                                max_message_size=maximum_message_size,
                                message_retention_seconds=message_retention_period,
                                fifo_queue=fifo_queue,
                                content_based_deduplication=content_based_deduplication,
                                kms_master_key_id=kms_master_key_id,
                                kms_data_key_reuse_period_seconds=kms_data_reuse_period,
                                visibility_timeout_seconds=vis_timeout,
                                policy=policy,
                                provider=provider)
        self.template.add_aws_sqs_queue(queue)

        if policy:
            tf_policy_name = build_terraform_resource_name(name,
                                                           'policy', region)
            sqs_policy = self._aws_sqs_queue_policy(
                tf_policy_name=tf_policy_name,
                policy=policy,
                tf_queue_name=tf_queue_name,
                provider=provider)
            self.template.add_aws_sqs_queue_policy(meta=sqs_policy)

    @staticmethod
    def _aws_sqs_queue_policy(tf_queue_name, tf_policy_name, policy,
                              provider=None):
        policy_meta = {
            'queue_url': build_sqs_queue_id_ref(queue_name=tf_queue_name),
            'policy': policy
        }

        if provider:
            policy_meta['provider'] = provider

        resource = {
            tf_policy_name: policy_meta
        }
        return resource

    def _sqs_queue(self, tf_queue_name, fifo_queue, queue_name,
                   delay_seconds,
                   receive_wait_time_seconds, max_message_size,
                   message_retention_seconds=None,
                   content_based_deduplication=None, kms_master_key_id=None,
                   kms_data_key_reuse_period_seconds=None,
                   visibility_timeout_seconds=None,
                   policy=None, redrive_policy=None,
                   provider=None):
        sqs_template = {}

        if fifo_queue:
            sqs_template.update({'fifo_queue': fifo_queue})

        if delay_seconds:
            sqs_template.update({'delay_seconds': delay_seconds})

        if max_message_size:
            sqs_template.update({'max_message_size': max_message_size})

        if queue_name:
            sqs_template.update({'name': queue_name})

        if receive_wait_time_seconds:
            sqs_template.update(
                {'receive_wait_time_seconds': receive_wait_time_seconds})

        if redrive_policy:
            redrive_policy = {
                'deadLetterTargetArn': redrive_policy['deadLetterTargetArn'],
                'maxReceiveCount': redrive_policy['maxReceiveCount']
            }
            sqs_template.update({'redrive_policy': json.dumps(redrive_policy)})

        if content_based_deduplication:
            sqs_template.update(
                {"content_based_deduplication": content_based_deduplication})

        if kms_master_key_id:
            sqs_template.update({'kms_master_key_id': kms_master_key_id})

        if kms_data_key_reuse_period_seconds:
            sqs_template.update({
                'kms_data_key_reuse_period_seconds': kms_data_key_reuse_period_seconds})

        if visibility_timeout_seconds:
            sqs_template.update(
                {'visibility_timeout_seconds': visibility_timeout_seconds})

        if policy:
            sqs_template.update({"policy": policy})

        if message_retention_seconds:
            sqs_template.update(
                {'message_retention_seconds': message_retention_seconds})

        if provider:
            sqs_template['provider'] = provider

        resource = {
            tf_queue_name: sqs_template
        }
        return resource

    @staticmethod
    def _build_redrive_policy(dead_letter_target_arn, max_receive_count):
        resource = {
            "deadLetterTargetArn": dead_letter_target_arn,
            "maxReceiveCount": max_receive_count
        }
        return resource

    @staticmethod
    def build_resource_name(is_fifo, name):
        resource_name = name
        if is_fifo and not name.endswith(FIFO_SUFFIX):
            resource_name += FIFO_SUFFIX
        return resource_name
