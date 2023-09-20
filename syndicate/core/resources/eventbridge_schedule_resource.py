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
import datetime
import ipaddress
import re
import string
from typing import Optional

from syndicate.commons.log_helper import get_logger
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, chunks, \
    validate_params, assert_possible_values

_LOG = get_logger('syndicate.core.resources.eventbridge_schedule_resource')

ALLOWED_KEYS = {'name', 'schedule_expression', 'state', 'description',
                'event_pattern', 'targets'}

REQUIRED_PARAMS = {'name', 'event_pattern', 'state', 'description', 'targets'}


def template_for_rule(params):
    name = params.get('name')
    validate_params(name, params, REQUIRED_PARAMS)
    validated_params = {}

    state = [params.get('state')]
    assert_possible_values(state, ['ENABLED', 'DISABLED'])

    start_date_str = params.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            if start_date < datetime.now():
                message = "Invalid 'start_date': It should be in future"
                _LOG.error(message)
                raise AssertionError(message)
        except ValueError:
            message = "Invalid 'start_date': It should be in ISO 8601 format."
            _LOG.error(message)
            raise AssertionError(message)


    return validated_params


class EventBridgeScheduleResource(BaseResource):

    def __init__(self, eventbridge_conn, iam_resource):
        self.connection = eventbridge_conn
        self.iam = iam_resource

    def create_schedule(self, args):
        return self.create_pool(self._create_schedule_from_meta, args)

    @unpack_kwargs
    def _create_schedule_from_meta(self, name, meta):
        """ Create EventBridge Schedule from meta description after parameter
        validation.

        :type name: str
        :type meta: dict
        """
        check_params = meta['schedule_content']
        check_params['name'] = name
        params = template_for_rule(check_params)

        response = self.connection.describe_schedule(name)
        if response:
            _arn = response['Arn']
            # TODO return error - already exists
            return self.describe_schedule(name, meta, _arn, response)

        arn = self.connection.create_rule(**params)
        _LOG.info(f'Created EventBridge rule {arn}')
        return self.describe_schedule(name=name, meta=meta, arn=arn)

    def describe_schedule(self, name, meta, arn, response=None):
        if not response:
            response = self.connection.describe_schedule(name)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def delete_schedule(self, args):
        return self.create_pool(self._delete_schedule, args)

    @unpack_kwargs
    def _delete_schedule(self, arn, config):
        name = config['resource_name']
        response = self.connection.delete_rule(name)
        return response
