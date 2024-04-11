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
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path, PurePath
from typing import Union

import yaml

from syndicate.commons.log_helper import get_logger
from syndicate.core.constants import BUILD_ACTION, \
    DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION, PACKAGE_META_ACTION, \
    PARTIAL_CLEAN_ACTION
from syndicate.core.constants import DATE_FORMAT_ISO_8601
from syndicate.core.groups import RUNTIME_JAVA, RUNTIME_NODEJS, RUNTIME_PYTHON, \
    RUNTIME_SWAGGER_UI

CAPITAL_LETTER_REGEX = '[A-Z][^A-Z]*'

STATE_NAME = 'name'
STATE_LOCKS = 'locks'
STATE_LAMBDAS = 'lambdas'
STATE_BUILD_PROJECT_MAPPING = 'build_projects_mapping'
STATE_LOG_EVENTS = 'events'
STATE_LATEST_DEPLOY = 'latest_deploy'
LOCK_LOCKED_TILL = 'locked_till'
LOCK_LAST_MODIFICATION_DATE = 'last_modification_date'
LOCK_INITIATOR = 'initiator'

MODIFICATION_LOCK = 'modification_lock'
WARMUP_LOCK = 'warm_up_lock'
PROJECT_STATE_FILE = '.syndicate'
INIT_FILE = '__init__.py'
INDEX_FILE = 'index.js'

BUILD_MAPPINGS = {
    RUNTIME_JAVA: 'jsrc/main/java',
    RUNTIME_PYTHON: 'src',
    RUNTIME_NODEJS: 'app',
    RUNTIME_SWAGGER_UI: 'swagger_src'
}

OPERATION_LOCK_MAPPINGS = {
    'deploy': MODIFICATION_LOCK
}
KEEP_EVENTS_DAYS = 30
LEAVE_LATEST_EVENTS = 20

_LOG = get_logger('project-state')


class ProjectState:

    def __init__(self, project_path: str = None, dct: dict = None):
        """In case 'dct' param is given it will be assigned to the internal
        _dict variable instead of loading from a file. It comes handy when
        we need to get ProjectState object without loading from file. All
        the existing functionality remains unimpaired"""
        if not (project_path or dct):
            message = 'Either project_path or dct of both must be ' \
                      'specified!'
            _LOG.error(message)
            raise AssertionError(message)
        if project_path:
            self.project_path = project_path
            self.state_path = os.path.join(project_path, PROJECT_STATE_FILE)
        self.dct = dct if dct else self.__load_project_state_file()

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

    @property
    def dct(self) -> dict:
        return self._dict

    @dct.setter
    def dct(self, dct: dict):
        self._dict = dct

    @staticmethod
    def get_remote() -> 'ProjectState':
        from syndicate.core import CONN, CONFIG
        bucket_name = CONFIG.deploy_target_bucket
        key_compound = PurePath(
            CONFIG.deploy_target_bucket_key_compound, PROJECT_STATE_FILE
        ).as_posix()
        s3 = CONN.s3()
        remote_project_state = s3.load_file_body(bucket_name=bucket_name,
                                                 key=key_compound)
        remote_project_state = yaml.unsafe_load(remote_project_state)
        _LOG.info(f'Unsafely loaded project state file from S3 bucket. The '
                  f'retrieved object has type: '
                  f'{type(remote_project_state).__name__}')
        if isinstance(remote_project_state, dict):
            remote_project_state = ProjectState(dct=remote_project_state)
            _LOG.info(f'Made ProjectState object from the dict loaded from S3 '
                      f'bucket')
        else:  # isinstance(remote_project_state, ProjectState):
            _LOG.warning(f'Loaded project state object is already instance of '
                         f'ProjectState. Likely .syndicate from the '
                         f'the bucket is obsolete. Rewriting...')
        return remote_project_state

    def save_to_remote(self, project_state_to_save: 'ProjectState' = None):
        dict_to_save = project_state_to_save.dct if \
            project_state_to_save else self.dct
        from syndicate.core import CONN, CONFIG
        bucket_name = CONFIG.deploy_target_bucket
        key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                PROJECT_STATE_FILE).as_posix()
        s3 = CONN.s3()
        s3.put_object(file_obj=yaml.dump(dict_to_save, sort_keys=False),
                      key=key_compound,
                      bucket=bucket_name,
                      content_type='application/x-yaml')

    def save(self):
        with open(self.state_path, 'w') as state_file:
            yaml.dump(self.dct, state_file, sort_keys=False)

    @property
    def name(self):
        return self.dct.get(STATE_NAME)

    @property
    def default_deploy_name(self):
        import re
        parts = []
        if '_' in self.name:
            parts.extend(self.name.split('_'))
        if not parts:
            parts = re.findall(CAPITAL_LETTER_REGEX, self.name)
        if not parts:
            parts = [self.name]
        return '-'.join([_.lower() for _ in parts])

    @name.setter
    def name(self, name):
        self.dct.update({STATE_NAME: name})

    @property
    def locks(self):
        locks = self.dct.get(STATE_LOCKS)
        if not locks:
            locks = dict()
            self.dct.update({STATE_LOCKS: locks})
        return locks

    @property
    def lambdas(self):
        lambdas = self.dct.get(STATE_LAMBDAS)
        if not lambdas:
            return dict()
        return lambdas

    @property
    def events(self):
        events = self.dct.get(STATE_LOG_EVENTS)
        if not events:
            events = []
            self.dct.update({STATE_LOG_EVENTS: events})
        return events

    @events.setter
    def events(self, events):
        self.dct.update({STATE_LOG_EVENTS: events})

    @property
    def latest_deploy(self):
        latest_deploy = self.dct.get(STATE_LATEST_DEPLOY)
        if not latest_deploy:
            latest_deploy = {}
            self.dct.update({STATE_LATEST_DEPLOY: latest_deploy})
        return latest_deploy

    @latest_deploy.setter
    def latest_deploy(self, latest_deploy):
        self.dct[STATE_LATEST_DEPLOY] = latest_deploy

    @property
    def latest_bundle_name(self):
        """Returns bundle_name from the one of the latest operations which
        can guarantee that the bundle is ready"""
        operations = [BUILD_ACTION, PACKAGE_META_ACTION]
        for event in self.events:
            if event.get('operation') in operations:
                bundle_name = event.get('bundle_name')
                if bundle_name:
                    return bundle_name

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
        modification_ops = [DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION]
        latest = next((event for event in events if
                       event.get('operation') in modification_ops), None)
        return latest

    def is_lock_free(self, lock_name):
        lock = self.locks.get(lock_name)
        if not lock:
            return True
        elif not lock.get(LOCK_LOCKED_TILL):
            return True
        elif locked_till := lock.get(LOCK_LOCKED_TILL):
            locked_till_datetime = datetime.strptime(
                locked_till, DATE_FORMAT_ISO_8601)
            if datetime.timestamp(locked_till_datetime) <= time.time():
                lock[LOCK_LOCKED_TILL] = None
                return True
        return False

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

    def actualize_latest_deploy(self, other_project_state: 'ProjectState'):
        local_deploy = self.latest_deploy
        remote_deploy = other_project_state.latest_deploy
        if local_deploy and remote_deploy:
            local_time_start = datetime.strptime(local_deploy['time_start'],
                                                 DATE_FORMAT_ISO_8601)
            remote_time_start = datetime.strptime(remote_deploy['time_start'],
                                                  DATE_FORMAT_ISO_8601)
            if remote_time_start > local_time_start:
                self.latest_deploy = remote_deploy
        elif remote_deploy:
            self.latest_deploy = remote_deploy

    def refresh_lambda_state(self):
        """
        Refreshes current Project lambda State, be resolving
        the compatibility with the retained state. Given any consistency
        conflict the ProjectState is re-persisted.
        :return: None
        """
        from syndicate.core.generators.lambda_function import \
            resolve_lambda_path
        from syndicate.core.helper import check_lambda_state_consistency

        _persistence_need: bool = False
        _project_path = Path(self.project_path)
        _stale_lambdas = self.lambdas
        for runtime, source in BUILD_MAPPINGS.items():
            _path = resolve_lambda_path(_project_path, runtime, source)
            _updated = self._update_lambdas_from_path(_path, runtime)
            if not _persistence_need and check_lambda_state_consistency(
                    objected_lambdas=_updated,
                    subjected_lambdas=_stale_lambdas,
                    runtime=runtime
            ):
                _persistence_need = True

        if _persistence_need:
            self.save()

    def _update_lambdas_from_path(self, path: Union[str, Path], runtime: str):
        """
        Non persistently updates ProjectState runtime and
        any found lambdas from a given path.
        :parameter path:Path
        :parameter runtime: str
        :return: List
        """
        try:
            path = path if isinstance(path, Path) else Path(path)
        except (TypeError, Exception):
            _LOG.error(f'Requested path {path} must be of str or Path type.')
            return []

        _LOG.info(f'Going to resolve any lambda names from a given path: '
                  f'{path.absolute()}.')
        _lambdas: list = self._resolve_lambdas_from_path(path, runtime)
        for name in self._resolve_lambdas_from_path(path, runtime):
            _LOG.info(f'Going to add the following \'{runtime}\' lambda:'
                      f'\'{name}\' to the pending ProjectState.')
            self.add_lambda(lambda_name=name, runtime=runtime)
        if _lambdas:
            self.add_project_build_mapping(runtime)
        return _lambdas

    def add_lambda(self, lambda_name, runtime):
        lambdas = self.dct.get(STATE_LAMBDAS)
        if not lambdas:
            lambdas = dict()
            self.dct.update({STATE_LAMBDAS: lambdas})
        lambdas.update({lambda_name: {'runtime': runtime}})

    def add_project_build_mapping(self, runtime):
        build_project_mappings = self.dct.get(STATE_BUILD_PROJECT_MAPPING)
        if not build_project_mappings:
            build_project_mappings = dict()
            self.dct.update(
                {STATE_BUILD_PROJECT_MAPPING: build_project_mappings})
        build_mapping = BUILD_MAPPINGS.get(runtime)
        build_project_mappings.update({runtime: build_mapping})

    def load_project_build_mapping(self):
        return self.dct.get(STATE_BUILD_PROJECT_MAPPING)

    def log_execution_event(self, **kwargs):
        operation = kwargs.get('operation')
        if operation in [DEPLOY_ACTION, PARTIAL_CLEAN_ACTION]:
            params = kwargs.copy()
            params.pop('operation')
            self._set_latest_deploy_info(**params)
        if operation == CLEAN_ACTION:
            self._delete_latest_deploy_info()

        kwargs = {key: value for key, value in kwargs.items() if value}
        self.events.insert(0, kwargs)
        self.__save_events()

    def _set_latest_deploy_info(self, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value}
        self.latest_deploy = kwargs

    def _delete_latest_deploy_info(self):
        self.latest_deploy = {}
        remote_project_state = ProjectState.get_remote()
        remote_project_state.latest_deploy = {}
        self.save_to_remote(project_state_to_save=remote_project_state)

    def add_execution_events(self, events):
        for event in events:
            if event not in self.events:
                self.events.append(event)
        self.events.sort(key=lambda e: e.get('time_end'), reverse=True)
        self.__save_events()

    def __modify_lock_state(self, lock_name, locked):
        from syndicate.core import CONFIG
        locked_till = CONFIG.lock_lifetime_minutes

        locks = self.locks
        lock = locks.get(lock_name)
        modification_datetime = datetime.fromtimestamp(time.time())
        timestamp = modification_datetime.strftime(DATE_FORMAT_ISO_8601)
        locked_till_timestamp = (modification_datetime +
                                 timedelta(minutes=locked_till)).strftime(
            DATE_FORMAT_ISO_8601)

        modified_lock = {
            LOCK_LAST_MODIFICATION_DATE: timestamp,
            LOCK_LOCKED_TILL: locked_till_timestamp if locked else None,
            LOCK_INITIATOR: getpass.getuser()
        }
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
        current_time = datetime.fromtimestamp(time.time())
        index_out_days = None
        for i, event in enumerate(self.events):
            if (current_time -
                datetime.strptime(event.get('time_end'),
                                  DATE_FORMAT_ISO_8601)).days > KEEP_EVENTS_DAYS:
                index_out_days = i
                break

        if index_out_days:
            if index_out_days >= LEAVE_LATEST_EVENTS:
                self.events = self.events[:index_out_days]
            else:
                self.events = self.events[:LEAVE_LATEST_EVENTS]
        self.save()

    @staticmethod
    def build_from_structure(config):
        """Builds project state file from existing project folder in case of
        moving from older versions
        :type config: syndicate.core.conf.processor.ConfigHolder
        """
        from syndicate.core.generators.lambda_function import \
            resolve_lambda_path
        absolute_path = config.project_path
        project_path = Path(absolute_path)
        project_state = ProjectState.generate(project_path=absolute_path,
                                              project_name=project_path.name)

        for runtime, source_path in BUILD_MAPPINGS.items():
            lambdas_path = resolve_lambda_path(project_path, runtime,
                                               source_path)
            if os.path.exists(lambdas_path):
                project_state.add_project_build_mapping(runtime)
                project_state._update_lambdas_from_path(lambdas_path, runtime)

        project_state.save()

        return project_state

    @staticmethod
    def _resolve_lambdas_from_path(path: Path, runtime: str):
        """
        Resolves a list of names bound to lambda functions,
        retained inside a given path, based on a provided runtime.
        :parameter path: Path
        :parameter runtime: str
        :return: List[str]
        """

        lambda_list = []
        _java_lambda_regex = 'lambdaName\s*=\s*"(.+)"'

        if not path.exists():
            return lambda_list

        for item in path.iterdir():
            if runtime == RUNTIME_JAVA:
                if not item.is_file():
                    continue
                try:
                    match = re.search(_java_lambda_regex, item.read_text())
                    if match:
                        lambda_list.append(match.group(1))
                except (OSError, Exception):
                    print("Couldn't retrieve lambda name from the java "
                          "lambda by path: {}".format(item.absolute()),
                          file=sys.stderr)
            else:
                if (item/INIT_FILE).exists() or (item/INDEX_FILE).exists():
                    lambda_list.append(item.name)

        return lambda_list
