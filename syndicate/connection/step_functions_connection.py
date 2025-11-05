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
from json import dumps

from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger(__name__)


@apply_methods_decorator(retry())
class SFConnection(object):
    """ STS connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('stepfunctions', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Step Functions connection.')

    def create_state_machine(self, machine_name, definition, role_arn, tags,
                             publish_version=False, version_description=None):
        if isinstance(definition, dict):
            definition = dumps(definition)
        params = dict(
            name=machine_name,
            definition=definition,
            roleArn=role_arn
        )

        if publish_version:
            params['publish'] = True
            if version_description:
                params['versionDescription'] = str(version_description)

        if tags:
            params['tags'] = tags

        return self.client.create_state_machine(**params)

    def update_state_machine(self, machine_arn, definition, role_arn,
                             publish_version=False, version_description=None):
        params = {
            'stateMachineArn': machine_arn,
            'roleArn': role_arn
        }

        if isinstance(definition, dict):
            params['definition'] = dumps(definition)

        if publish_version:
            params['publish'] = True
            if version_description:
                params['versionDescription'] = str(version_description)
        return self.client.update_state_machine(**params)

    def create_state_machine_alias(self, name, routing_config,
                                   description=None):
        params = {
            'name': name,
            'routingConfiguration': routing_config
        }
        if description:
            params['description'] = description
        response = self.client.create_state_machine_alias(**params)
        return response['stateMachineAliasArn']

    def update_state_machine_alias(self, arn, routing_config,
                                   description=None):
        params = {
            'stateMachineAliasArn': arn,
            'routingConfiguration': routing_config
        }
        if description:
            params['description'] = description
        self.client.update_state_machine_alias(**params)

    def describe_state_machine(self, arn):
        try:
            return self.client.describe_state_machine(stateMachineArn=arn)
        except ClientError as e:
            if 'StateMachineDoesNotExist' in str(e):
                pass  # valid exception
            else:
                raise e

    def describe_state_machine_alias(self, arn):
        try:
            return self.client.describe_state_machine_alias(
                stateMachineAliasArn=arn)
        except ClientError as e:
            if 'ResourceNotFound' in str(e):
                pass  # valid exception
            else:
                raise e

    def delete_state_machine(self, arn, log_not_found_error=True):
        """
        log_not_found_error parameter is needed for proper log handling in the
        retry decorator
        """
        return self.client.delete_state_machine(stateMachineArn=arn)

    def list_state_machines(self):
        result = []
        response = self.client.list_state_machines()
        do_continue = response.get('nextToken')
        if 'stateMachines' in response:
            result.extend([i['name'] for i in response['stateMachines']])
        while do_continue:
            response = self.client.list_state_machines(nextToken=do_continue)
            do_continue = response.get('nextToken')
            if 'stateMachines' in response:
                result.extend([i['name'] for i in response['stateMachines']])
        return result

    def list_executions_by_status(self, state_machine_arn, execution_status):
        result = []
        response = self.client.list_executions(
            stateMachineArn=state_machine_arn,
            statusFilter=execution_status
        )
        do_continue = response.get('nextToken')
        if 'executions' in response:
            result.extend(response['executions'])
        while do_continue:
            response = self.client.list_executions(
                stateMachineArn=state_machine_arn,
                statusFilter=execution_status,
                nextToken=do_continue
            )
            do_continue = response.get('nextToken')
            if 'executions' in response:
                result.extend(response['executions'])
        return result

    def stop_execution(self, execution_arn):
        return self.client.stop_execution(executionArn=execution_arn)

    def create_activity(self, name, tags):
        params = dict(
            name=name
        )
        if tags:
            params['tags'] = tags
        return self.client.create_activity(name=name)

    def describe_activity(self, arn):
        try:
            return self.client.describe_activity(activityArn=arn)
        except ClientError as e:
            if 'ActivityDoesNotExist' in str(e):
                pass  # valid exception
            else:
                raise e

    def delete_activity(self, arn, log_not_found_error=True):
        """
        log_not_found_error parameter is needed for proper log handling in the
        retry decorator
        """
        self.client.delete_activity(activityArn=arn)

    def list_activities(self):
        result = []
        response = self.client.list_activities()
        do_continue = response.get('nextToken')
        if 'activities' in response:
            result.extend([i['name'] for i in response['activities']])
        while do_continue:
            response = self.client.list_activities(nextToken=do_continue)
            do_continue = response.get('nextToken')
            if 'activities' in response:
                result.extend([i['name'] for i in response['activities']])
        return result
