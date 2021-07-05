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
        policy_json = json.dumps(policy)

        dead_letter_target_arn = resource.get('deadLetterTargetArn')
        max_receive_count = resource.get('maxReceiveCount')
        redrive_policy = build_redrive_policy(
            dead_letter_target_arn=dead_letter_target_arn,
            max_receive_count=max_receive_count)
        redrive_policy_json = json.dumps(redrive_policy)

        kms_master_key_id = resource.get('kms_master_key_id')
        kms_data_key_reuse_period_seconds = resource.get(
            'kms_data_key_reuse_period_seconds')

        queue = sqs_queue(queue_name=name, redrive_policy=redrive_policy_json,
                          delay_seconds=delay_seconds,
                          receive_wait_time_seconds=receive_message_wait_time_seconds,
                          max_message_size=maximum_message_size,
                          message_retention_seconds=message_retention_period,
                          fifo_queue=fifo_queue,
                          content_based_deduplication=content_based_deduplication,
                          kms_master_key_id=kms_master_key_id,
                          kms_data_key_reuse_period_seconds=kms_data_key_reuse_period_seconds,
                          visibility_timeout_seconds=visibility_timeout,
                          policy=policy_json)
        self.template.add_aws_sqs_queue(queue)


def sqs_queue(queue_name, redrive_policy, delay_seconds,
              receive_wait_time_seconds, max_message_size,
              message_retention_seconds, fifo_queue,
              content_based_deduplication, kms_master_key_id,
              kms_data_key_reuse_period_seconds, visibility_timeout_seconds,
              policy):
    resource = {
        queue_name: [
            {
                "delay_seconds": delay_seconds,
                "max_message_size": max_message_size,
                "message_retention_seconds": message_retention_seconds,
                "name": queue_name,
                "receive_wait_time_seconds": receive_wait_time_seconds,
                "redrive_policy": redrive_policy,
                "tags": tags,
                "fifo_queue": fifo_queue,
                "content_based_deduplication": content_based_deduplication,
                "kms_master_key_id": kms_master_key_id,
                "kms_data_key_reuse_period_seconds": kms_data_key_reuse_period_seconds,
                "visibility_timeout_seconds": visibility_timeout_seconds,
                "policy": policy
            }
        ]
    }
    return resource


def build_redrive_policy(dead_letter_target_arn, max_receive_count):
    resource = {
        "deadLetterTargetArn": dead_letter_target_arn,
        "maxReceiveCount": max_receive_count
    }
    return resource
