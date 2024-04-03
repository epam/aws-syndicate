from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.eventbridge_scheduler_connection')


@apply_methods_decorator(retry())
class EventBridgeSchedulerConnection(object):
    """ EventBridge Scheduler Connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('scheduler', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new EventBridge Scheduler connection.')

    def create_schedule(self, **params):
        return self.client.create_schedule(**params)['ScheduleArn']

    def update_schedule(self, **params):
        return self.client.update_schedule(**params)['ScheduleArn']

    def describe_schedule(self, name, group_name=None):
        params = {'Name': name}
        if group_name is not None:
            params['GroupName'] = group_name

        try:
            return self.client.get_schedule(**params)

        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                _LOG.warning(
                    f'Cannot find EventBridge schedule with name {name}')
                return None
            else:
                raise e

    def delete_schedule(self, name, group_name=None):
        params = {'Name': name}
        if group_name is not None:
            params['GroupName'] = group_name

        return self.client.delete_schedule(**params)