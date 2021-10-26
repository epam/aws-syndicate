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
import getpass
import os
import time
from datetime import datetime

import yaml

from syndicate.core.groups import RUNTIME_JAVA, RUNTIME_NODEJS, RUNTIME_PYTHON
from syndicate.core.constants import DATE_FORMAT_ISO_8601

CAPITAL_LETTER_REGEX = '[A-Z][^A-Z]*'

STATE_NAME = 'name'
STATE_LOCKS = 'locks'
STATE_LAMBDAS = 'lambdas'
STATE_BUILD_PROJECT_MAPPING = 'build_projects_mapping'
STATE_LOG_EVENTS = 'events'
STATE_LATEST_DEPLOY = 'latest_deploy'
LOCK_LOCKED = 'locked'
LOCK_LAST_MODIFICATION_DATE = 'last_modification_date'
LOCK_INITIATOR = 'initiator'

MODIFICATION_LOCK = 'modification_lock'
WARMUP_LOCK = 'warm_up_lock'
PROJECT_STATE_FILE = '.syndicate'

BUILD_MAPPINGS = {
    RUNTIME_JAVA: 'jsrc/main/java',
    RUNTIME_PYTHON: 'src',
    RUNTIME_NODEJS: 'app'
}

OPERATION_LOCK_MAPPINGS = {
    'deploy': MODIFICATION_LOCK
}
KEEP_EVENTS_DAYS = 30
LEAVE_LATEST_EVENTS = 20

class ProjectState:

    def __init__(self, project_path):
        self.project_path = project_path
        self.state_path = os.path.join(project_path, PROJECT_STATE_FILE)
        self._dict = self.__load_project_state_file()

    @staticmethod
    def generate(project_path, project_name):
        project_state = dict(name=project_name)
        with open(os.path.join(project_path, PROJECT_STATE_FILE),
                  'w') as state_file:
            yaml.dump(project_state, state_file)
        return ProjectState(project_path=project_path)

    @staticmethod
    def check_if_project_state_exists(project_path):
        return os.path.exists(os.path.join(project_path, PROJECT_STATE_FILE))

    def save(self):
        with open(self.state_path, 'w') as state_file:
            yaml.dump(self._dict, state_file, sort_keys=False)

    @property
    def name(self):
        return self._dict.get(STATE_NAME)

    @property
    def default_deploy_name(self):
        import re
        parts = []
        if '_' in self.name:
            parts.extend(self.name.split('_'))
        if not parts:
            parts = re.findall(CAPITAL_LETTER_REGEX, self.name)
        return '-'.join([_.lower() for _ in parts])

    @name.setter
    def name(self, name):
        self._dict.update({STATE_NAME: name})

    @property
    def locks(self):
        locks = self._dict.get(STATE_LOCKS)
        if not locks:
            locks = dict()
            self._dict.update({STATE_LOCKS: locks})
        return locks

    @property
    def lambdas(self):
        lambdas = self._dict.get(STATE_LAMBDAS)
        if not lambdas:
            return dict()
        return lambdas

    @property
    def events(self):
        events = self._dict.get(STATE_LOG_EVENTS)
        if not events:
            events = []
            self._dict.update({STATE_LOG_EVENTS:
                                   events})
        return events

    @events.setter
    def events(self, events):
        self._dict.update({STATE_LOG_EVENTS: events})

    @property
    def latest_deploy(self):
        latest_deploy = self._dict.get(STATE_LATEST_DEPLOY)
        if not latest_deploy:
            latest_deploy = {}
            self._dict.update({STATE_LATEST_DEPLOY: latest_deploy})
        return latest_deploy

    @latest_deploy.setter
    def latest_deploy(self, latest_deploy):
        self._dict[STATE_LATEST_DEPLOY] = latest_deploy


    @property
    def latest_built_bundle_name(self):
        return self._get_attribute_from_latest_operation(operation_name='build',
                                                  attribute='bundle_name')

    @property
    def latest_built_deploy_name(self):
        return self._get_attribute_from_latest_operation(operation_name='build',
                                                  attribute='deploy_name')

    @property
    def latest_deployed_bundle_name(self):
        return self.latest_deploy.get('bundle_name')

    @property
    def latest_deployed_deploy_name(self):
        return self.latest_deploy.get('deploy_name')

    def _get_attribute_from_latest_operation(self, operation_name, attribute):
        events = self.events
        event = next((event for event in events if
                      event.get('operation') == operation_name), None)
        if event:
            return event.get(attribute)

    @property
    def latest_modification(self):
        events = self.events
        modification_ops = ['deploy', 'update', 'clean']
        latest = next((event for event in events if
                       event.get('operation') in modification_ops), None)
        return latest

    def is_lock_free(self, lock_name):
        lock = self.locks.get(lock_name)
        if not lock:
            return True
        return not bool(lock.get(LOCK_LOCKED))

    def acquire_lock(self, lock_name):
        self.__modify_lock_state(lock_name, True)

    def release_lock(self, lock_name):
        self.__modify_lock_state(lock_name, False)

    def actualize_locks(self, other_project_state):
        locks = self.locks
        other_locks = other_project_state.locks
        all_lock_names = set(locks.keys()).union(set(other_locks.keys()))
        for lock_name in all_lock_names:
            lock = locks.get(lock_name)
            other_lock = other_locks.get(lock_name)
            if lock is None:
                locks.update({lock_name: other_lock})
            elif other_lock is None:
                other_locks.update({lock_name: lock})
            elif (lock.get(LOCK_LAST_MODIFICATION_DATE) <
                  other_lock.get(LOCK_LAST_MODIFICATION_DATE)):
                locks.update({lock_name: other_lock})
            else:
                other_locks.update({lock_name: lock})

    def add_lambda(self, lambda_name, runtime):
        lambdas = self._dict.get(STATE_LAMBDAS)
        if not lambdas:
            lambdas = dict()
            self._dict.update({STATE_LAMBDAS: lambdas})
        lambdas.update({lambda_name: {'runtime': runtime}})

    def add_project_build_mapping(self, runtime):
        build_project_mappings = self._dict.get(STATE_BUILD_PROJECT_MAPPING)
        if not build_project_mappings:
            build_project_mappings = dict()
            self._dict.update(
                {STATE_BUILD_PROJECT_MAPPING: build_project_mappings})
        build_mapping = BUILD_MAPPINGS.get(runtime)
        build_project_mappings.update({runtime: build_mapping})

    def load_project_build_mapping(self):
        return self._dict.get(STATE_BUILD_PROJECT_MAPPING)

    def log_execution_event(self, **kwargs):
        operation = kwargs.get('operation')
        if operation == 'deploy':
            self._set_latest_deploy_info(**kwargs)
        if operation == 'clean':
            self._delete_latest_deploy_info()

        kwargs = {key: value for key, value in kwargs.items() if value}
        self.events.append(kwargs)
        self.__save_events()

    def _set_latest_deploy_info(self, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value}
        del kwargs['operation']
        self.latest_deploy = kwargs

    def _delete_latest_deploy_info(self):
        self.latest_deploy = {}

    def add_execution_events(self, events):
        all_events = self.events
        all_events.extend(x for x in events if x not in all_events)
        self.__save_events()

    def __modify_lock_state(self, lock_name, locked):
        locks = self.locks
        lock = locks.get(lock_name)
        timestamp = datetime.fromtimestamp(time.time()) \
            .strftime(DATE_FORMAT_ISO_8601)
        modified_lock = {LOCK_LOCKED: locked,
                         LOCK_LAST_MODIFICATION_DATE: timestamp,
                         LOCK_INITIATOR: getpass.getuser()}
        if lock:
            lock.update(modified_lock)
        else:
            locks.update({lock_name: modified_lock})
        self.save()

    def __load_project_state_file(self):
        if not ProjectState.check_if_project_state_exists(self.project_path):
            raise AssertionError(
                f'There is no .syndicate file in {self.project_path}')
        with open(self.state_path) as state_file:
            return yaml.safe_load(state_file.read())

    def __save_events(self):
        self.events.sort(key=lambda event: event.get('time_start'),
                         reverse=True)
        current_time = datetime.fromtimestamp(time.time())
        index_out_days = None
        for i, event in enumerate(self.events):
            if (current_time -
                datetime.strptime(event.get('time_start'),
                                  DATE_FORMAT_ISO_8601)).days > KEEP_EVENTS_DAYS:
                index_out_days = i
                break

        if index_out_days:
            if index_out_days >= LEAVE_LATEST_EVENTS:
                self.events = self.events[:index_out_days]
            else:
                self.events = self.events[:LEAVE_LATEST_EVENTS]
        self.save()
