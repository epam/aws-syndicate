import os
import json

from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger(__name__)


class LambdaExample(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass
        
    def handle_request(self, event, context):
        json_region = os.environ['AWS_REGION']
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(
                {
                    "Region ": json_region
                }
            )
        }

HANDLER = LambdaExample()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)
