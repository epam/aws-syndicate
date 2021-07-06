import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class SQSQueueConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        fifo_queue = resource.get('fifo_queue')
        visibility_timeout = resource.get('visibility_timeout')
        delay_seconds = resource.get('delay_seconds')
        maximum_message_size = resource.get('maximum_message_size')
        message_retention_period = resource.get('message_retention_period')
        receive_message_wait_time_seconds = resource.get(
            'receive_message_wait_time_seconds')
        content_based_deduplication = resource.get(
            'content_based_deduplication')

        policy = resource.get('policy')
        if policy:
            policy = json.dumps(policy)

        redrive_policy = None
        dead_letter_target_arn = resource.get('deadLetterTargetArn')
        max_receive_count = resource.get('maxReceiveCount')
        if dead_letter_target_arn and max_receive_count:
            redrive_policy = json.dumps(build_redrive_policy(
                dead_letter_target_arn=dead_letter_target_arn,
                max_receive_count=max_receive_count))

        kms_master_key_id = resource.get('kms_master_key_id')
        kms_data_key_reuse_period_seconds = resource.get(
            'kms_data_key_reuse_period_seconds')

        queue = sqs_queue(queue_name=name, redrive_policy=redrive_policy,
                          delay_seconds=delay_seconds,
                          receive_wait_time_seconds=receive_message_wait_time_seconds,
                          max_message_size=maximum_message_size,
                          message_retention_seconds=message_retention_period,
                          fifo_queue=fifo_queue,
                          content_based_deduplication=content_based_deduplication,
                          kms_master_key_id=kms_master_key_id,
                          kms_data_key_reuse_period_seconds=kms_data_key_reuse_period_seconds,
                          visibility_timeout_seconds=visibility_timeout,
                          policy=policy)
        self.template.add_aws_sqs_queue(queue)


def sqs_queue(fifo_queue, queue_name, delay_seconds,
              receive_wait_time_seconds, max_message_size,
              message_retention_seconds=None,
              content_based_deduplication=None, kms_master_key_id=None,
              kms_data_key_reuse_period_seconds=None,
              visibility_timeout_seconds=None,
              policy=None, redrive_policy=None):
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
        sqs_template.update({'redrive_policy': redrive_policy})

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

    resource = {
        queue_name: sqs_template
    }
    return resource


def build_redrive_policy(dead_letter_target_arn, max_receive_count):
    resource = {
        "deadLetterTargetArn": dead_letter_target_arn,
        "maxReceiveCount": max_receive_count
    }
    return resource
