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

_LOG = get_logger('syndicate.connection.ses_connection')


@apply_methods_decorator(retry)
class SESConnection(object):
    """SES connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, source_arn=None,
                 aws_session_token=None):
        self.client = client('ses', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        self.charset = 'utf-8'
        self.arn = source_arn
        self.source_email = source_arn[source_arn.index('/') + 1:]
        _LOG.debug('Opened new SES connection.')

    def send_email_from_identity(self, to_addresses, cc_addresses=None,
                                 bcc_addresses=None, reply_to_addresses=None,
                                 subject='', body_type='Html', body='body'):
        """
        Method for sending message from specified arn in AWS SES.
        :type to_addresses: list
        :type cc_addresses: list
        :type bcc_addresses: list
        :type reply_to_addresses: list
        :type subject: str
        :param body_type: 'Html'/'Text'
        :type body: str
        """
        cc_addresses = cc_addresses if cc_addresses else []
        bcc_addresses = bcc_addresses if bcc_addresses else []
        reply_to_addresses = reply_to_addresses if reply_to_addresses else []
        response = self.client.send_email(
            Source=self.source_email,
            Destination={
                'ToAddresses': to_addresses,
                'CcAddresses': cc_addresses,
                'BccAddresses': bcc_addresses
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': self.charset
                },
                'Body': {
                    body_type: {
                        'Data': body,
                        'Charset': self.charset
                    }
                }
            },
            ReplyToAddresses=reply_to_addresses,
            ReturnPath=self.source_email,
            SourceArn=self.arn,
            ReturnPathArn=self.arn
        )
        return response
