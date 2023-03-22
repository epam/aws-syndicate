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
from boto3 import client

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.sts_connection')


@apply_methods_decorator(retry)
class STSConnection(object):
    """ STS connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('sts', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new STS connection.')

    def get_temp_credentials(self, role_arn, acc_id, duration=None,
                             serial_number=None, token_code=None):
        """ Get temporary credentials by assuming role
        :param role_arn: str
        :param acc_id: str
        :param duration: int
        :param serial_number: str
        :param token_code: int
        """
        duration = 3600 if not duration else duration
        arn = 'arn:aws:iam::{0}:role/{1}'.format(acc_id, role_arn)
        session_name = "session_{0}".format(acc_id)
        params = dict(
            RoleArn=arn,
            RoleSessionName=session_name,
            DurationSeconds=duration
        )
        if serial_number and token_code:
            params['SerialNumber'] = serial_number
            params['TokenCode'] = token_code
        response = self.client.assume_role(**params)
        return response['Credentials']

    def get_session_token(self, duration=3600, serial_number=None,
                          token_code=None):
        """ Generates temporary AWS credentials

        :param duration: int - duration, in seconds, that the credentials
            should remain valid. From 900 (15 min) to 129600 (36h)
        :param serial_number: str - The identification number of the MFA
            device that is associated with the IAM user who is making the call
        :param token_code: int - The value provided by the MFA device,
            if MFA is required.

        """
        kwargs = {
            'DurationSeconds': duration,
            'SerialNumber': serial_number,
            'TokenCode': token_code
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        response = self.client.get_session_token(**kwargs)
        return response['Credentials']

    def get_caller_identity(self):
        """ Returns details about the IAM identity whose credentials are used to call the API.
        """
        return self.client.get_caller_identity()
