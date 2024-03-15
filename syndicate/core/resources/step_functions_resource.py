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
import time

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)

_LOG = get_logger('core.resources.step_function_resource')


class StepFunctionResource(BaseResource):

    def __init__(self, sf_conn, iam_conn, cw_events_conn, lambda_conn,
                 account_id, region) -> None:
        self.sf_conn = sf_conn
        self.iam_conn = iam_conn
        self.cw_events_conn = cw_events_conn
        self.lambda_conn = lambda_conn
        self.account_id = account_id
        self.region = region

    def create_state_machine(self, args):
        return self.create_pool(self._create_state_machine_from_meta, args)

    def create_activities(self, args):
        return self.create_pool(self._create_activity_from_meta, args)

    def remove_state_machines(self, args):
        self.create_pool(self._remove_state_machine, args)
        if args:
            time.sleep(60)

    @unpack_kwargs
    def _remove_state_machine(self, arn, config):
        sm_name = config['resource_name']
        try:
            executions = self.sf_conn.list_executions_by_status(arn, 'RUNNING')
            if executions:
                _LOG.debug('Found {0} running executions '
                           'for {1}'.format(len(executions), sm_name))
                for execution in executions:
                    self.sf_conn.stop_execution(execution['executionArn'])
                _LOG.debug('Executions stop initiated')
            self.sf_conn.delete_state_machine(arn)
            _LOG.info('State machine %s was removed', sm_name)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'StateMachineDoesNotExist':
                _LOG.warn('State machine %s is not found', sm_name)
            else:
                raise e

    def remove_activities(self, args):
        self.create_pool(self._remove_activity, args)

    @unpack_kwargs
    def _remove_activity(self, arn, config):
        activity_name = config['resource_name']
        try:
            self.sf_conn.delete_activity(arn)
            _LOG.info('State activity %s was removed', activity_name)
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'ResourceNotFoundException':
                _LOG.warn('State activity %s is not found', activity_name)
            else:
                raise e

    def __remove_key_from_dict(self, obj, name):
        try:
            del obj[name]
        except KeyError:
            pass

    @unpack_kwargs
    def _create_state_machine_from_meta(self, name, meta):
        arn = self._build_sm_arn(name, self.region)
        response = self.sf_conn.describe_state_machine(arn)
        if response:
            _LOG.warn('State machine %s exists', name)
            return {
                arn: build_description_obj(response, name, meta)
            }

        iam_role = meta['iam_role']
        role_arn = self.iam_conn.check_if_role_exists(iam_role)
        if not role_arn:
            raise AssertionError(
                'IAM role {0} does not exist.'.format(iam_role))

        # check resource exists and get arn
        definition = meta['definition']
        definition_copy = definition.copy()
        for key in definition['States']:
            definition_meta = definition['States'][key]
            if definition_meta.get('Lambda'):
                lambda_name = definition_meta['Lambda']
                # alias has a higher priority than version in arn resolving
                lambda_version = definition_meta.get('Lambda_version')
                lambda_alias = definition_meta.get('Lambda_alias')
                lambda_arn = self.resolve_lambda_arn_by_version_and_alias(
                    lambda_name,
                    lambda_version,
                    lambda_alias)
                self.__remove_key_from_dict(definition_copy['States'][key],
                                            'Lambda')
                self.__remove_key_from_dict(definition_copy['States'][key],
                                            'Lambda_version')
                self.__remove_key_from_dict(definition_copy['States'][key],
                                            'Lambda_alias')

                definition_copy['States'][key]['Resource'] = lambda_arn

            if definition_meta.get('Activity'):
                activity_name = definition_meta['Activity']
                activity_arn = 'arn:aws:states:{0}:{1}:activity:{2}'.format(
                    self.region, self.account_id, activity_name)
                activity_info = self.sf_conn.describe_activity(
                    arn=activity_arn)
                if not activity_info:
                    raise AssertionError('Activity does not exists: %s',
                                         activity_name)
                activity_arn = activity_info['activityArn']
                del definition_copy['States'][key]['Activity']
                definition_copy['States'][key]['Resource'] = activity_arn
        machine_info = self.sf_conn.create_state_machine(machine_name=name,
                                                         role_arn=role_arn,
                                                         definition=definition_copy)

        event_sources = meta.get('event_sources')
        if event_sources:
            for trigger_meta in event_sources:
                trigger_type = trigger_meta['resource_type']
                func = self.CREATE_TRIGGER[trigger_type]
                func(name, trigger_meta)
        _LOG.info('Created state machine %s.', machine_info['stateMachineArn'])
        return self.describe_step_function(name=name, meta=meta, arn=arn)

    def describe_step_function(self, name, meta, arn=None):
        if not arn:
            arn = self._build_sm_arn(name, self.region)
        response = self.sf_conn.describe_state_machine(arn)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def _build_sm_arn(self, name, region):
        return f'arn:aws:states:{region}:{self.account_id}:stateMachine:{name}'

    def _create_cloud_watch_trigger_from_meta(self, name, trigger_meta):
        required_parameters = ['target_rule', 'input', 'iam_role']
        validate_params(name, trigger_meta, required_parameters)
        rule_name = trigger_meta['target_rule']
        input = trigger_meta['input']
        sf_role = trigger_meta['iam_role']

        sf_arn = self._build_sm_arn(name, self.region)
        sf_description = self.sf_conn.describe_state_machine(arn=sf_arn)
        if sf_description.get('status') == 'ACTIVE':
            sf_role_arn = self.iam_conn.check_if_role_exists(sf_role)
            if sf_role_arn:
                self.cw_events_conn.add_rule_sf_target(rule_name, sf_arn,
                                                       input,
                                                       sf_role_arn)
                _LOG.info('State machine %s subscribed to cloudwatch rule %s',
                          name, rule_name)

    CREATE_TRIGGER = {
        'cloudwatch_rule_trigger': _create_cloud_watch_trigger_from_meta,
        'eventbridge_rule_trigger': _create_cloud_watch_trigger_from_meta
    }

    @unpack_kwargs
    def _create_activity_from_meta(self, name, meta):
        arn = self.build_activity_arn(name=name)
        response = self.sf_conn.describe_activity(arn)
        if response:
            _LOG.warn('Activity %s exists.', name)
            return {
                arn: build_description_obj(response, name, meta)
            }
        response = self.sf_conn.create_activity(name=name)
        _LOG.info('Activity %s is created.', name)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_activity(self, name, meta):
        arn = self.build_activity_arn(name=name)
        response = self.sf_conn.describe_activity(arn=arn)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def build_activity_arn(self, name):
        arn = 'arn:aws:states:{0}:{1}:activity:{2}'.format(self.region,
                                                           self.account_id,
                                                           name)
        return arn
