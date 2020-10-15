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

    def get_temp_credentials(self, role_arn, acc_id, duration=None):
        """ Get temporary credentials by assuming role.

        :param role_arn: str
        :param acc_id: str
        :param duration: int

        """
        duration = 3600 if not duration else duration
        arn = 'arn:aws:iam::{0}:role/{1}'.format(acc_id, role_arn)
        session_name = "session_{0}".format(acc_id)
        response = self.client.assume_role(
            RoleArn=arn,
            RoleSessionName=session_name,
            DurationSeconds=duration
        )
        return response['Credentials']
