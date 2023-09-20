from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.firehose_connection')


@apply_methods_decorator(retry)
class EventBridgeScheduleConnection(object):
    """ EventBridge Schedule Connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('events', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new EventBridge Schedule connection.')

    def create_rule(self, **params):

        # params = {
        #     'Name': name,
        #     'ScheduleExpression': schedule_expression,
        #     'State': state
        # }
        # if description:
        #     params['Description'] = description
        return self.client.put_rule(**params)['RuleArn']

    # def describe_rule(self, name):
    #     params = {'Name': name}
    #     try:
    #         return self.client.describe_schedule(**params)['Rule']
    #     except ClientError as e:
    #         if 'ResourceNotFoundException' in str(e):
    #             _LOG.warning(
    #                 f'Cannot find EventBridge rule with name {name}')
    #             pass
    #         else:
    #             raise e

    def delete_rule(self, name):
        try:
            return self.client.delete_rule(Name=name)
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                _LOG.warning(
                    f'Cannot find EventBridge rule with name {name}')
                pass
            else:
                raise e

    def describe_schedule(self, name):
        params = {'Name': name}
        try:
            return self.client.describe_rule(**params)

        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                _LOG.warning(
                    f'Cannot find EventBridge schedule with name {name}')
                return None
            else:
                raise e
