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

_LOG = get_logger(
    'syndicate.connection.resource_groups_tagging_api_connection')


class ResourceGroupsTaggingAPIConnection:
    """Resource Groups Tagging API connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.client = client('resourcegroupstaggingapi', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Resource Groups Tagging API connection.')

    def tag_resources(self, resources_arns: list, tags: dict):
        params = dict(ResourceARNList=resources_arns,
                      Tags=tags)
        response = self.client.tag_resources(**params)
        return response.get('FailedResourcesMap')

    def untag_resources(self, resources_arns: list, tag_keys: list):
        params = dict(ResourceARNList=resources_arns,
                      TagKeys=tag_keys)
        response = self.client.untag_resources(**params)
        return response.get('FailedResourcesMap')
