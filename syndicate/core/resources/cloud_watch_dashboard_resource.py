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

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params, \
    build_description_obj
from syndicate.exceptions import ResourceNotFoundError, \
    ResourceProcessingError

CLOUDWATCH_DASHBOARD_REQUIRED_PARAMS = ['dashboard_body']

_LOG = get_logger(__name__)

class CloudWatchDashboardResource(BaseResource):

    def __init__(
            self,
            cw_dashboard_conn,
    ) -> None:
        self.client = cw_dashboard_conn

    def describe_dashboard(
            self,
            name: str,
            meta: dict,
    ) -> dict:
        response = self.client.get_dashboard(name)
        if not response:
            return {}
        arn = response['DashboardArn']
        return {
            arn: build_description_obj(response, name, meta)
        }

    def create_dashboard(self, args):
        """ Create dashboard in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_dashboard_from_meta, args)

    def update_dashboard(self, args):
        """ Update dashboard in pool in sub processes."""
        return self.create_pool(self._update_dashboard_from_meta, args)

    def remove_dashboard(self, args):
        """ Remove dashboard from pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._remove_dashboard, args)

    @unpack_kwargs
    def _create_dashboard_from_meta(
            self,
            name: str,
            meta: dict,
    ) -> dict:
        """ Create Cloud Watch Dashboard resource in AWS Cloud via meta description.

        :type name: str
        :type meta: dict
        """
        _LOG.info(f"Creating Cloud Watch Dashboard {name}")

        if self.client.get_dashboard(name):
            _LOG.warning(f'{name} dashboard exists.')
            return self.describe_dashboard(name, meta)

        self._create_update_dashboard(name, meta)

        _LOG.info(f'Created dashboard {name}.')
        return self.describe_dashboard(name, meta)

    @unpack_kwargs
    def _update_dashboard_from_meta(
            self,
            name: str,
            meta: dict,
            context: dict,
    ):

        if not self.client.get_dashboard(name):
            _LOG.warning(f'CloudWatch dashboard {name}  does not exist.')
            raise ResourceNotFoundError(
                f"'{name}' dashboard does not exist."
            )

        self._create_update_dashboard(name, meta)

        _LOG.info(f'Updated dashboard {name}.')
        return self.describe_dashboard(name, meta)

    @unpack_kwargs
    def _remove_dashboard(
            self,
            arn: str,
            config: dict,
    ) -> dict:
        _LOG.info(f'Removing dashboard {arn}.')
        name = config['resource_name']
        if not self.client.get_dashboard(name):
            _LOG.warning(f'{name} dashboard does not exist.')
            return {arn: config}

        self.client.delete_dashboards(name)
        _LOG.info(f'Removed dashboard {name}.')

        return {arn: config}

    def _create_update_dashboard(
            self,
            name: str,
            meta: dict,
    ):
        validate_params(name, meta, CLOUDWATCH_DASHBOARD_REQUIRED_PARAMS)

        params = dict(
            dashboard_name=name,
            dashboard_body=meta['dashboard_body'],
            tags=meta.get('tags'),
        )

        messages = self.client.put_dashboard(**params)

        if messages:
            message = f"During processing dashboard '{name}' the following errors occurred: {messages}"
            _LOG.warning(message)
            raise ResourceProcessingError(message)
