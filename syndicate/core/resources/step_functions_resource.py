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

from syndicate.exceptions import ResourceNotFoundError
from syndicate.commons.log_helper import get_logger
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import (build_description_obj,
                                             validate_params)
DEFAULT_ROUTING_CONFIG_WEIGHT = 100

_LOG = get_logger(__name__)


class StepFunctionResource(BaseResource):

    def __init__(self, sf_conn, iam_conn, cw_events_conn, lambda_conn,
                 lambda_res, account_id, region) -> None:
        self.sf_conn = sf_conn
        self.iam_conn = iam_conn
        self.cw_events_conn = cw_events_conn
        self.lambda_conn = lambda_conn
        self.lambda_res = lambda_res
        self.account_id = account_id
        self.region = region
        self.CREATE_TRIGGER = {
            'cloudwatch_rule_trigger':
                self._create_cloud_watch_trigger_from_meta,
            'eventbridge_rule_trigger':
                self._create_cloud_watch_trigger_from_meta
        }

    def create_state_machine(self, args):
        return self.create_pool(self._create_state_machine_from_meta, args)

    def update_state_machine(self, args):
        return self.create_pool(self._update_state_machine, args)

    def create_activities(self, args):
        return self.create_pool(self._create_activity_from_meta, args)

    def remove_state_machines(self, args):
        result = self.create_pool(self._remove_state_machine, args)
        if args:
            time.sleep(60)

        return result

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
            self.sf_conn.delete_state_machine(arn, log_not_found_error=False)
            _LOG.info('State machine %s was removed', sm_name)
            return {arn: config}
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'StateMachineDoesNotExist':
                _LOG.warn('State machine %s is not found', sm_name)
                return {arn: config}
            else:
                raise e

    def remove_activities(self, args):
        return self.create_pool(self._remove_activity, args)

    @unpack_kwargs
    def _remove_activity(self, arn, config):
        activity_name = config['resource_name']
        try:
            self.sf_conn.delete_activity(arn, log_not_found_error=False)
            _LOG.info('State activity %s was removed', activity_name)
            return {arn: config}
        except ClientError as e:
            exception_type = e.response['Error']['Code']
            if exception_type == 'ResourceNotFoundException':
                _LOG.warn('State activity %s is not found', activity_name)
                return {arn: config}
            else:
                raise e

    def __remove_key_from_dict(self, obj, name):
        try:
            del obj[name]
        except KeyError:
            pass

    @unpack_kwargs
    def _create_state_machine_from_meta(self, name, meta):
        definition = meta.get('definition', {})
        publish_version = meta.get('publish_version', False)
        version_description = meta.get('version_description')
        alias_name = meta.get('alias')
        alias_description = meta.get('alias_description')
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
            raise ResourceNotFoundError(
                f"IAM role '{iam_role}' does not exist."
            )

        machine_info = self.sf_conn.create_state_machine(
            machine_name=name,
            role_arn=role_arn,
            definition=self._resolve_sm_definition(definition),
            publish_version=publish_version,
            version_description=version_description,
            tags=meta.get('tags'),
        )

        alias_arn = None
        if alias_name is not None:
            if publish_version:
                alias_arn = self._create_state_machine_alias(
                    name=alias_name,
                    version_arn=machine_info['stateMachineVersionArn'],
                    description=alias_description)
                _LOG.debug(f"An alias with ARN '{alias_arn}' was created "
                           f"successfully.")
            else:
                _LOG.warn(f"The alias with the name '{alias_name}' can't be "
                          f"created because no publishing version is "
                          f"configured.")

        event_sources = meta.get('event_sources', [])
        self._process_event_sources(
            sf_name=name,
            event_sources=event_sources,
            alias_name=alias_name if alias_arn else None)
        _LOG.info('Created state machine %s.', machine_info['stateMachineArn'])
        return self.describe_step_function(name=name, meta=meta, arn=arn)

    def _create_state_machine_alias(self, name, version_arn, description=None):
        routing_config = [
            {
                'stateMachineVersionArn': version_arn,
                'weight': DEFAULT_ROUTING_CONFIG_WEIGHT
            }
        ]
        return self.sf_conn.create_state_machine_alias(
            name=name,
            routing_config=routing_config,
            description=description
        )

    @unpack_kwargs
    def _update_state_machine(self, name, meta, context):
        definition = meta.get('definition', {})
        publish_version = meta.get('publish_version', False)
        version_description = meta.get('version_description')
        alias_name = meta.get('alias')
        alias_description = meta.get('alias_description')

        sf_arn = self._build_sm_arn(name, self.region)
        response = self.sf_conn.describe_state_machine(sf_arn)
        if not response:
            raise AssertionError(f"Step function with name '{name}' not found")

        iam_role = meta['iam_role']
        role_arn = self.iam_conn.check_if_role_exists(iam_role)
        if not role_arn:
            raise AssertionError(
                'IAM role {0} does not exist.'.format(iam_role))

        machine_info = self.sf_conn.update_state_machine(
            machine_arn=sf_arn,
            role_arn=role_arn,
            definition=self._resolve_sm_definition(definition),
            publish_version=publish_version,
            version_description=version_description)

        alias_arn = None
        if alias_name is not None:
            if publish_version:
                alias_arn = f"{sf_arn}:{alias_name}"
                if self.sf_conn.describe_state_machine_alias(alias_arn):
                    self._update_state_machine_alias(
                        arn=alias_arn,
                        version_arn=machine_info['stateMachineVersionArn'],
                        description=alias_description)
                    _LOG.debug(f"An alias with ARN '{alias_arn}' was updated "
                               f"successfully.")
                else:
                    alias_arn = self._create_state_machine_alias(
                        name=alias_name,
                        version_arn=machine_info['stateMachineVersionArn'],
                        description=alias_description)
                    _LOG.debug(f"An alias with ARN '{alias_arn}' was created "
                               f"successfully.")
            else:
                _LOG.warn(f"The alias with the name '{alias_name}' can't be "
                          f"updated because no publishing version is "
                          f"configured.")

        event_sources = meta.get('event_sources', [])
        self._process_event_sources(
            sf_name=name,
            event_sources=event_sources,
            alias_name=alias_name if alias_arn else None)
        _LOG.info(f'Updated state machine {sf_arn}.')
        return self.describe_step_function(name=name, meta=meta, arn=sf_arn)

    def _update_state_machine_alias(self, arn, version_arn, description=None):
        routing_config = [
            {
                'stateMachineVersionArn': version_arn,
                'weight': DEFAULT_ROUTING_CONFIG_WEIGHT
            }
        ]
        return self.sf_conn.update_state_machine_alias(
            arn=arn,
            routing_config=routing_config,
            description=description
        )

    def describe_step_function(self, name, meta, arn=None):
        if not arn:
            arn = self._build_sm_arn(name, self.region)
        response = self.sf_conn.describe_state_machine(arn)
        if response:
            return {
                arn: build_description_obj(response, name, meta)
            }
        return {}

    def _build_sm_arn(self, name, region):
        return f'arn:aws:states:{region}:{self.account_id}:stateMachine:{name}'

    def _process_event_sources(self, sf_name, event_sources, alias_name=None):
        for trigger_meta in event_sources:
            trigger_type = trigger_meta['resource_type']
            func = self.CREATE_TRIGGER[trigger_type]
            func(sf_name, trigger_meta, alias_name)

    def _create_cloud_watch_trigger_from_meta(self, name, trigger_meta,
                                              alias_name=None):
        required_parameters = ['target_rule', 'input', 'iam_role']
        validate_params(name, trigger_meta, required_parameters)
        rule_name = trigger_meta['target_rule']
        input = trigger_meta['input']
        sf_role = trigger_meta['iam_role']

        sf_arn = self._build_sm_arn(name, self.region)
        target_arn = f'{sf_arn}:{alias_name}' if alias_name else sf_arn
        sf_description = self.sf_conn.describe_state_machine(arn=sf_arn)
        if sf_description.get('status') == 'ACTIVE':
            sf_role_arn = self.iam_conn.check_if_role_exists(sf_role)
            if sf_role_arn:
                self.cw_events_conn.add_rule_sf_target(
                    rule_name=rule_name,
                    target_arn=target_arn,
                    input=input,
                    role_arn=sf_role_arn)
                _LOG.info('State machine %s subscribed to cloudwatch rule %s',
                          name, rule_name)

    @unpack_kwargs
    def _create_activity_from_meta(self, name, meta):
        arn = self.build_activity_arn(name=name)
        response = self.sf_conn.describe_activity(arn)
        if response:
            _LOG.warn('Activity %s exists.', name)
            return {
                arn: build_description_obj(response, name, meta)
            }
        response = self.sf_conn.create_activity(name=name,
                                                tags=meta.get('tags'))
        _LOG.info('Activity %s is created.', name)
        return {
            arn: build_description_obj(response, name, meta)
        }

    def describe_activity(self, name, meta):
        arn = self.build_activity_arn(name=name)
        response = self.sf_conn.describe_activity(arn=arn)
        if response:
            return {
                arn: build_description_obj(response, name, meta)
            }
        return {}

    def build_activity_arn(self, name):
        arn = 'arn:aws:states:{0}:{1}:activity:{2}'.format(self.region,
                                                           self.account_id,
                                                           name)
        return arn

    def _resolve_sm_definition(self, definition):
        # check resource exists and get arn
        definition_copy = definition.copy()
        for key in definition.get('States', {}):
            definition_meta = definition['States'][key]
            if definition_meta.get('Lambda'):
                lambda_name = definition_meta['Lambda']
                # alias has a higher priority than version in arn resolving
                lambda_version = definition_meta.get('Lambda_version')
                lambda_alias = definition_meta.get('Lambda_alias')
                lambda_arn = \
                    self.lambda_res.resolve_lambda_arn_by_version_and_alias(
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

        return definition_copy
