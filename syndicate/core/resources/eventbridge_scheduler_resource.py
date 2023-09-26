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
from datetime import datetime, timezone

from syndicate.commons.log_helper import get_logger
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs
from syndicate.core.helper import dict_keys_to_capitalized_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, \
    validate_params, assert_possible_values

_LOG = get_logger('syndicate.core.resources.eventbridge_scheduler_resource')

REQUIRED_PARAMS = {'name', 'schedule_expression', 'state', 'description',
                   'flexible_time_window'}


def convert_to_datetime(name, date_str):
    try:
        if len(date_str) > 10:
            return datetime.fromisoformat(date_str)
        else:
            return datetime.utcfromtimestamp(int(date_str))
    except (ValueError, OSError):
        raise AssertionError(
            f'Invalid date format: {date_str}. Resource: {name}. Should be ISO8601 or timestamp'
            )


def prepare_schedule_parameters(meta):
    name = meta.get('name')
    validate_params(name, meta, REQUIRED_PARAMS)
    params = meta.copy()

    # keys inside "Target" parameters should NOT be changed to PascalCase
    # syndicate user responsible for providing Target's key-values pairs in proper format
    target = params.pop('target')
    params = dict_keys_to_capitalized_camel_case(params)
    params['Target'] = target

    assert_possible_values([params.get('State')],
                           ['ENABLED', 'DISABLED']) \
        if 'State' in params else None
    assert_possible_values([params.get('FlexibleTimeWindow').get('Mode')],
                           ['OFF', 'FLEXIBLE']) \
        if 'Mode' in params.get('FlexibleTimeWindow') else None

    if 'StartDate' in params:
        start_date = convert_to_datetime(name, params.get('StartDate'))
        if start_date <= datetime.now(timezone.utc):
            raise ValueError('Start date must be in the future.')
    if 'EndDate' in params:
        end_date = convert_to_datetime(name, params.get('EndDate'))
        if start_date <= datetime.now(timezone.utc):
            raise ValueError('End date must be in the future.')

    if 'StartDate' in params and 'EndDate' in params:
        if start_date >= end_date:
            raise ClientError('Start date must be earlier than end date.')

    return params


class EventBridgeSchedulerResource(BaseResource):

    def __init__(self, eventbridge_conn):
        self.connection = eventbridge_conn

    def create_schedule(self, args):
        return self.create_pool(self._create_schedule_from_meta, args)

    @unpack_kwargs
    def _create_schedule_from_meta(self, name, meta):
        _LOG.debug(f'Creating schedule {name}')
        check_params = meta['schedule_content']
        check_params['name'] = name
        params = prepare_schedule_parameters(check_params)
        group_name = check_params.get('group_name')
        response = self.connection.describe_schedule(name, group_name)
        if response:
            _arn = response['Arn']
            # TODO return error - already exists
            return self.describe_schedule(name, group_name, meta, _arn,
                                          response)

        arn = self.connection.create_schedule(**params)
        _LOG.info(f'Created EventBridge schedule {arn}')
        return self.describe_schedule(name=name, group_name=group_name,
                                      meta=meta, arn=arn)

    def update_schedule(self, args):
        return self.create_pool(self._update_schedule_from_meta, args)

    @unpack_kwargs
    def _update_schedule_from_meta(self, name, meta, context):
        """ Create EventBridge Schedule from meta description after parameter
        validation.

        :type name: str
        :type meta: dict
        """
        check_params = meta['schedule_content']
        check_params['name'] = name
        group_name = check_params.get('group_name')
        response = self.connection.describe_schedule(name, group_name)
        if not response:
            raise AssertionError(f'{name} schedule does not exist.')

        params = prepare_schedule_parameters(check_params)
        _arn = response['Arn']

        arn = self.connection.update_schedule(**params)
        _LOG.info(f'Updated EventBridge schedule {arn}')
        return self.describe_schedule(name=name, group_name=group_name,
                                      meta=meta, arn=arn)

    def describe_schedule(self, name, group_name, meta, arn, response=None):
        if not response:
            response = self.connection.describe_schedule(name, group_name)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def remove_schedule(self, args):
        return self.create_pool(self._remove_schedule, args)

    @unpack_kwargs
    def _remove_schedule(self, arn, config):
        name = config['resource_name']
        try:
            group_name = config['resource_meta']['schedule_content'].get(
                'group_name')
        except:
            group_name = None
        return self.connection.delete_schedule(name=name, group_name=group_name)
