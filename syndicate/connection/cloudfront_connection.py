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

_LOG = get_logger('syndicate.connection.cloud_front_connection')


@apply_methods_decorator(retry)
class CloudFrontConnection(object):
    """ CloudFront Connection class"""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.client = client('cloudfront', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Cloudfront connection.')

    def get_distribution_config(self, distribution_id):
        """ Crescribes cloud front distribution configuration.

        :type distribution_id: str
        :return: distribution
        """
        return self.client.get_distribution_config(Id=distribution_id)

    def create_distribution(self, distribution_config):
        """ Creates cloud front distribution.

        :type distribution_config: dict
        :return: distribution
        """
        return self.client.create_distribution(
            DistributionConfig=distribution_config)

    def create_invalidation(self, distribution_id, items, quantity,
                            caller_reference):
        inv_params = {
            'Paths':
                {
                    'Quantity': quantity,
                    'Items': items
                },
            'CallerReference': caller_reference
        }
        return self.client.create_invalidation(DistributionId=distribution_id,
                                               InvalidationBatch=inv_params)
