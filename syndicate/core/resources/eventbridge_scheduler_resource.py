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
from time import sleep

from syndicate.exceptions import InvalidValueError, ResourceNotFoundError
from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs, convert_to_datetime, \
    as_utc_aware
from syndicate.core.helper import dict_keys_to_capitalized_camel_case
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, \
    validate_params, assert_possible_values

_LOG = get_logger(__name__)

REQUIRED_PARAMS = {'name', 'schedule_expression', 'state', 'description',
                   'flexible_time_window'}


class EventBridgeSchedulerResource(BaseResource):

    def __init__(self, eventbridge_conn):
        self.connection = eventbridge_conn

    @staticmethod
    def prepare_schedule_parameters(meta: dict):
        name = meta.get('name')
        validate_params(name, meta, REQUIRED_PARAMS)
        params = meta.copy()

        params = dict_keys_to_capitalized_camel_case(params)

        assert_possible_values([params.get('State')],
                               ['ENABLED', 'DISABLED']) \
            if 'State' in params else None
        flexible = params.get('FlexibleTimeWindow')
        if isinstance(flexible, dict) and 'Mode' in flexible:
            assert_possible_values([flexible.get('Mode')],
                                   ['OFF', 'FLEXIBLE'])

        now_utc = datetime.now(timezone.utc)
        start_date = None
        end_date = None
        if 'StartDate' in params:
            start_date = as_utc_aware(
                convert_to_datetime(name, params.get('StartDate')))
            if start_date <= now_utc:
                raise InvalidValueError('Start date must be in the future.')
        if 'EndDate' in params:
            end_date = as_utc_aware(
                convert_to_datetime(name, params.get('EndDate')))
            if end_date <= now_utc:
                raise InvalidValueError('End date must be in the future.')

        if start_date is not None and end_date is not None:
            if start_date >= end_date:
                raise InvalidValueError(
                    'Start date must be earlier than end date.'
                )

        return params

    def create_schedule(self, args):
        sleep(4)  # sometimes role does not have time to be created
        # and this leads to an error
        return self.create_pool(self._create_schedule_from_meta, args)

    @unpack_kwargs
    def _create_schedule_from_meta(self, name, meta):
        _LOG.debug(f'Creating schedule {name}')
        check_params = {**meta['schedule_content'], 'name': name}
        params = self.prepare_schedule_parameters(check_params)
        response = self.describe_schedule(name, meta)
        if response:
            return response

        arn = self.connection.create_schedule(**params)
        _LOG.info(f'Created EventBridge schedule {arn}')
        return self.describe_schedule(name=name, meta=meta)

    def update_schedule(self, args):
        return self.create_pool(self._update_schedule_from_meta, args)

    @unpack_kwargs
    def _update_schedule_from_meta(self, name, meta, context):
        """
        Update EventBridge Schedule from meta description after parameter
        validation.

        :type name: str
        :type meta: dict
        """
        check_params = {**meta['schedule_content'], 'name': name}
        group_name = check_params.get('group_name')
        response = self.connection.describe_schedule(name, group_name)
        if not response:
            raise ResourceNotFoundError(f"'{name}' schedule does not exist.")

        params = self.prepare_schedule_parameters(check_params)

        arn = self.connection.update_schedule(**params)
        _LOG.info(f'Updated EventBridge schedule {arn}')
        return self.describe_schedule(name=name, meta=meta)

    def describe_schedule(self, name, meta):
        group_name = meta.get('group_name')

        response = self.connection.describe_schedule(name, group_name)
        if response:
            arn = response['Arn']
            return {
                arn: build_description_obj(response, name, meta)
            }
        return {}

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
        self.connection.delete_schedule(name=name,
                                        group_name=group_name,
                                        log_not_found_error=False)
        return {arn: config}
