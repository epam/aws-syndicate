from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import SQS_QUEUE_TYPE


class SQSQueueGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = SQS_QUEUE_TYPE
    CONFIGURATION = {
        "fifo_queue": bool,
        "region": None,
        "visibility_timeout": 30,  # seconds
        "delay_seconds": 0,
        "maximum_message_size": 1024,  # bytes
        "message_retention_period": 60,  # seconds
        "receive_message_wait_time_seconds": 0,
        "policy": dict,
        "redrive_policy": {
            "deadLetterTargetArn": None,
            "maxReceiveCount": None,
        },
        "kms_master_key_id": None,
        "kms_data_key_reuse_period_seconds": None,
        "content_based_deduplication": False
    }

    def __init__(self, **kwargs):
        if 'dead_letter_target_arn' in kwargs:
            kwargs['deadLetterTargetArn'] = kwargs.pop(
                'dead_letter_target_arn')
            kwargs['maxReceiveCount'] = kwargs.pop('max_receive_count')
        super().__init__(**kwargs)
