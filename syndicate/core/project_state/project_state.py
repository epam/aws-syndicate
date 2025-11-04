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
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePath
from typing import Union

import yaml

from syndicate.exceptions import InternalError, ProjectStateError
from syndicate.commons.log_helper import get_logger
from syndicate.core.constants import BUILD_ACTION, \
    DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION, PACKAGE_META_ACTION, \
    ABORTED_STATUS, SUCCEEDED_STATUS, FAILED_STATUS, FAILED_RETURN_CODE, \
    OK_RETURN_CODE, ABORTED_RETURN_CODE, MODIFICATION_OPS
from syndicate.core.constants import DATE_FORMAT_ISO_8601
from syndicate.core.groups import RUNTIME_JAVA, RUNTIME_NODEJS, RUNTIME_PYTHON, \
    RUNTIME_SWAGGER_UI, RUNTIME_DOTNET, RUNTIME_APPSYNC, JAVA_ROOT_DIR_JAPP, \
    NODEJS_ROOT_DIR, PYTHON_ROOT_DIR_PYAPP, DOTNET_ROOT_DIR, \
    SWAGGER_UI_ROOT_DIR, APPSYNC_ROOT_DIR, JAVA_ROOT_DIR_JSRC, \
    PYTHON_ROOT_DIR_SRC

CAPITAL_LETTER_REGEX = '[A-Z][^A-Z]*'

STATE_NAME = 'name'
STATE_LOCKS = 'locks'
STATE_LAMBDAS = 'lambdas'
STATE_BUILD_PROJECT_MAPPING = 'build_projects_mapping'
STATE_LOG_EVENTS = 'events'
STATE_LATEST_DEPLOY = 'latest_deploy'
LOCK_LOCKED_TILL = 'locked_till'
LOCK_IS_LOCKED = 'is_locked'
LOCK_LAST_MODIFICATION_DATE = 'last_modification_date'
LOCK_INITIATOR = 'initiator'

MODIFICATION_LOCK = 'modification_lock'
WARMUP_LOCK = 'warm_up_lock'
PROJECT_STATE_FILE = '.syndicate'
LAMBDA_CONFIG_FILE = 'lambda_config.json'

BUILD_MAPPINGS = {
    RUNTIME_JAVA: JAVA_ROOT_DIR_JAPP,
    RUNTIME_PYTHON: PYTHON_ROOT_DIR_PYAPP,
    RUNTIME_NODEJS: NODEJS_ROOT_DIR,
    RUNTIME_DOTNET: DOTNET_ROOT_DIR,
    RUNTIME_SWAGGER_UI: SWAGGER_UI_ROOT_DIR,
    RUNTIME_APPSYNC: APPSYNC_ROOT_DIR
}

LEGACY_BUILD_MAPPINGS = {
    RUNTIME_JAVA: JAVA_ROOT_DIR_JSRC,
    RUNTIME_PYTHON: PYTHON_ROOT_DIR_SRC
}

OPERATION_LOCK_MAPPINGS = {
    'deploy': MODIFICATION_LOCK
}
KEEP_EVENTS_DAYS = 30
LEAVE_LATEST_EVENTS = 20

_LOG = get_logger(__name__)


class ProjectState:

    def __init__(self, project_path: str = None, dct: dict = None):
        """In case 'dct' param is given it will be assigned to the internal
        _dict variable instead of loading from a file. It comes handy when
        we need to get ProjectState object without loading from file. All
        the existing functionality remains unimpaired"""
        from syndicate.core import CONF_PATH

        if not (project_path or dct):
            raise InternalError(
                "Either 'project_path' or 'dct' of both must be specified!"
            )
        if project_path:
            self.project_path = project_path
            self.state_path = os.path.join(CONF_PATH, PROJECT_STATE_FILE)
        self.dct = dct if dct else self.__load_project_state_file()
        self._current_deploy = None
        self._current_bundle = None

    @staticmethod
    def generate(project_path, project_name):
        from syndicate.core import CONF_PATH

        project_state = dict(name=project_name)
        with open(os.path.join(CONF_PATH, PROJECT_STATE_FILE),
                  'w') as state_file:
            yaml.dump(project_state, state_file)
        return ProjectState(project_path=project_path)

    @staticmethod
    def check_if_project_state_exists(project_state_path: str) -> bool:
        return os.path.exists(
            os.path.join(project_state_path, PROJECT_STATE_FILE)
        )

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
    def current_deploy(self):
        return self._current_deploy

    @current_deploy.setter
    def current_deploy(self, current_deploy):
        self._current_deploy = current_deploy

    @property
    def current_bundle(self):
        return self._current_bundle

    @current_bundle.setter
    def current_bundle(self, current_bundle):
        self._current_bundle = current_bundle

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
        latest = next((event for event in events if
                       event.get('operation') in MODIFICATION_OPS), None)
        return latest

    def get_latest_deployed_or_updated_bundle(
            self, bundle_name=None, latest_if_not_found=False):
        """
        Retrieve the latest deployed or updated bundle. If `bundle_name`
        is provided, it returns the latest event for that specific bundle.
        If `bundle_name` is None, it returns the latest event across all
        operations.
        :latest_if_not_found: - If True, the method will retry fetching the
        latest event without reference to the bundle name.
        """
        if bundle_name:
            modification_ops = [DEPLOY_ACTION, UPDATE_ACTION, CLEAN_ACTION]
        else:
            modification_ops = [DEPLOY_ACTION, UPDATE_ACTION]
        filtered_events = (
            event for event in self.events
            if self._is_event_matching(event, bundle_name, modification_ops)
        )
        latest_event = next(filtered_events, None)
        if latest_event and latest_event.get('operation') == CLEAN_ACTION:
            # in case bundle was deleted manually but present in .syndicate
            return self.get_latest_deployed_or_updated_bundle()

        if not latest_event and latest_if_not_found:
            return self.get_latest_deployed_or_updated_bundle()
        return latest_event.get('bundle_name') if latest_event else None

    @staticmethod
    def _is_event_matching(event, bundle_name, modification_ops):
        matches_operation = event.get('operation') in modification_ops
        matches_bundle_name = bundle_name is None or event.get(
            'bundle_name') == bundle_name
        status = event.get('status') != ABORTED_STATUS

        return matches_operation and matches_bundle_name and status

    def is_lock_free(self, lock_name=None, lock_config=None):
        lock = lock_config or self.locks.get(lock_name)
        if not lock:
            return True
        elif not lock.get(LOCK_IS_LOCKED):
            return True
        elif locked_till := lock.get(LOCK_LOCKED_TILL):
            locked_till_datetime = datetime.strptime(
                locked_till, DATE_FORMAT_ISO_8601)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if locked_till_datetime <= now:
                lock[LOCK_LOCKED_TILL] = None
                lock[LOCK_IS_LOCKED] = False
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
            elif (not self.is_lock_free(lock_config=other_lock) and
                  getpass.getuser() != other_lock.get(LOCK_INITIATOR)):
                locks.update({lock_name: other_lock})
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

    def refresh_state(self):
        """
        Refreshes current Project State, be resolving
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
            if runtime in [RUNTIME_SWAGGER_UI, RUNTIME_APPSYNC]:
                _updated = self._update_bpm_resources_from_path(_path, runtime)
                if not _persistence_need and _updated:
                    _persistence_need = True
            else:
                _updated = self._update_lambdas_from_path(_path, runtime)
                if not _persistence_need and check_lambda_state_consistency(
                        objected_lambdas=_updated,
                        subjected_lambdas=_stale_lambdas,
                        runtime=runtime
                ):
                    _persistence_need = True

        if _persistence_need:
            self.save()

    def _check_legacy_path(
        self, 
        runtime: str, 
        current_path: Path,
    ) -> tuple[Path, list]:
        """
        Check legacy path structure for lambdas if none found in current path.
        :param runtime: Runtime type
        :param current_path: Current path being checked
        :return: Tuple of (path, lambdas_list)
        """
        from syndicate.core.generators.lambda_function import resolve_lambda_path
        
        if runtime not in LEGACY_BUILD_MAPPINGS:
            return current_path, []
            
        legacy_runtime_root_dir = LEGACY_BUILD_MAPPINGS[runtime]
        legacy_path = resolve_lambda_path(
            Path(self.project_path), runtime, legacy_runtime_root_dir
        )
        
        if os.path.exists(legacy_path):
            _LOG.info(
                f'No {runtime} lambdas found in the {BUILD_MAPPINGS[runtime]!r} '
                f'dir. Checking the {legacy_runtime_root_dir!r} dir for '
                f'{runtime} lambdas.'
            )
            lambdas = self._resolve_lambdas_from_path(legacy_path, runtime)
            _LOG.info(
                f'Found the following {runtime} lambdas in the '
                f'{legacy_runtime_root_dir!r} dir: {lambdas}.'
            )
            return legacy_path, lambdas
            
        return current_path, []

    def _add_build_mapping_for_runtime(
        self, 
        runtime: str, 
        path: Path, 
        lambdas: list,
    ) -> None:
        """
        Add build mapping based on runtime and path structure.
        :param runtime: Runtime type
        :param path: Current path
        :param lambdas: List of found lambdas
        """
        if not lambdas:
            return

        if runtime in LEGACY_BUILD_MAPPINGS:
            legacy_runtime_root_dir = LEGACY_BUILD_MAPPINGS[runtime]
            actual_runtime_root_dir = BUILD_MAPPINGS[runtime]
            path_as_posix = path.as_posix()

            is_legacy_path = (
                legacy_runtime_root_dir in path_as_posix and 
                actual_runtime_root_dir not in path_as_posix
            )
            
            if is_legacy_path:
                self.add_project_build_mapping(
                    runtime,
                    build_mapping=legacy_runtime_root_dir,
                )
            else:
                self.add_project_build_mapping(runtime)
        else:
            self.add_project_build_mapping(runtime)

    def _update_lambdas_from_path(self, path: Union[str, Path], runtime: str):
        """
        Non persistently updates ProjectState runtime and
        any found lambdas from a given path.
        :parameter path: Path
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
        
        lambdas = self._resolve_lambdas_from_path(path, runtime)
        
        if not lambdas:
            path, lambdas = self._check_legacy_path(runtime, path)

        for name in lambdas:
            _LOG.info(f'Going to add the following \'{runtime}\' lambda:'
                      f'\'{name}\' to the pending ProjectState.')
            self.add_lambda(lambda_name=name, runtime=runtime)
        
        self._add_build_mapping_for_runtime(runtime, path, lambdas)
        
        return lambdas

    def add_lambda(self, lambda_name, runtime):
        lambdas = self.dct.get(STATE_LAMBDAS)
        if not lambdas:
            lambdas = dict()
            self.dct.update({STATE_LAMBDAS: lambdas})
        lambdas.update({lambda_name: {'runtime': runtime}})

    def _update_bpm_resources_from_path(self,
                                        path: Union[str, Path],
                                        runtime: str) -> list:
        """
        Non persistently updates ProjectState runtime and
        any found build project mapping dependent resources from a given path.
        :parameter path:Path
        :parameter runtime: str
        :return: List
        """
        try:
            path = path if isinstance(path, Path) else Path(path)
        except (TypeError, Exception):
            _LOG.error(f'Requested path {path} must be of str or Path type.')
            return []

        _LOG.info(
            f'Going to resolve any build project mapping dependent resources '
            f'from a given path: {path.absolute()}.'
        )
        build_project_mappings: dict | None = self.dct.get(
            STATE_BUILD_PROJECT_MAPPING
        )
        _bpm_resources = self._resolve_bpm_resources_from_path(path, runtime)

        missing_build_project_mapping = (
            not build_project_mappings or 
            runtime not in build_project_mappings
        )
        if _bpm_resources and (missing_build_project_mapping):
            _LOG.info(
                f'Going to add build project mapping for the following '
                f'resource type\'{runtime}\' to the pending ProjectState.')
            self.add_project_build_mapping(runtime)
            return _bpm_resources
        return []

    def add_project_build_mapping(self, runtime, build_mapping=None):
        build_project_mappings = self.dct.get(STATE_BUILD_PROJECT_MAPPING)
        if not build_project_mappings:
            build_project_mappings = dict()
            self.dct.update(
                {STATE_BUILD_PROJECT_MAPPING: build_project_mappings})
        build_mapping = build_mapping or BUILD_MAPPINGS.get(runtime)
        build_project_mappings.update({runtime: build_mapping})

    def load_project_build_mapping(self):
        return self.dct.get(STATE_BUILD_PROJECT_MAPPING)

    def log_execution_event(self, **kwargs):
        from syndicate.core import CONFIG, CONN
        from syndicate.core.build.bundle_processor import \
            build_output_key
        operation = kwargs.get('operation')
        status = kwargs.get('status')
        rollback_on_error = kwargs.get('rollback_on_error')
        valid_statuses = {
            FAILED_RETURN_CODE, OK_RETURN_CODE, ABORTED_RETURN_CODE
        }

        if status not in valid_statuses:
            kwargs.pop('status', None)
        else:
            status = {
                OK_RETURN_CODE: True,
                FAILED_RETURN_CODE: False,
                ABORTED_RETURN_CODE: ABORTED_STATUS,
                None: None
            }.get(status)

        if operation in (DEPLOY_ACTION, UPDATE_ACTION):
            params = kwargs.copy()
            params.pop('operation', None)
            params.pop('status', None)
            params['is_succeeded'] = status

            if params['is_succeeded'] != ABORTED_STATUS:
                s3 = CONN.s3()
                bundle_name = params.get('bundle_name')
                deploy_name = params.get('deploy_name')

                keys_to_check = [
                    PurePath(
                        CONFIG.deploy_target_bucket_key_compound,
                        build_output_key(bundle_name, deploy_name, True)
                    ).as_posix(),
                    PurePath(
                        CONFIG.deploy_target_bucket_key_compound,
                        build_output_key(bundle_name, deploy_name, False)
                    ).as_posix(),
                ]

                output_file_exist = any(
                    s3.is_file_exists(CONFIG.deploy_target_bucket, key)
                    for key in keys_to_check
                )

                skip_rollback = not (
                        status is False and rollback_on_error is True
                )

                if skip_rollback and output_file_exist:
                    params.pop('rollback_on_error')
                    self._set_latest_deploy_info(**params)
    
        if operation == CLEAN_ACTION and status is True:
            self._delete_latest_deploy_info()

        match status:
            case True:
                kwargs['status'] = SUCCEEDED_STATUS
            case False:
                kwargs['status'] = FAILED_STATUS
            case status if status == ABORTED_STATUS:
                kwargs['status'] = ABORTED_STATUS

        kwargs = {
            key: value for key, value in kwargs.items() if value is not None
        }
        self.events.insert(0, kwargs)
        self.__save_events()

    def _set_latest_deploy_info(self, **kwargs):
        kwargs = {
            key: value for key, value in kwargs.items() if value is not None
        }
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
        modification_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
        timestamp = modification_datetime.strftime(DATE_FORMAT_ISO_8601)
        locked_till_timestamp = (modification_datetime +
                                 timedelta(minutes=locked_till)).strftime(
            DATE_FORMAT_ISO_8601)

        modified_lock = {
            LOCK_LAST_MODIFICATION_DATE: timestamp,
            LOCK_IS_LOCKED: locked,
            LOCK_INITIATOR: getpass.getuser()
        }
        if locked:
            modified_lock[LOCK_LOCKED_TILL] = locked_till_timestamp

        if lock:
            if not locked:
                lock.pop(LOCK_LOCKED_TILL, None)
            lock.update(modified_lock)
        else:
            locks.update({lock_name: modified_lock})
        self.save()

    def __load_project_state_file(self):
        from syndicate.core import CONF_PATH

        if not ProjectState.check_if_project_state_exists(CONF_PATH):
            raise ProjectStateError(
                f"There is no '.syndicate' file in '{CONF_PATH}'"
            )
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
    def build_from_structure(config: "ProjectState"):
        """Builds project state file from existing project folder in case of
        moving from older versions
        :type config: syndicate.core.conf.processor.ConfigHolder
        """
        from syndicate.core.generators.lambda_function import \
            resolve_lambda_path
        absolute_path = config.project_path
        project_path = Path(absolute_path)
        project_state = ProjectState.generate(
            project_path=absolute_path, project_name=project_path.name
        )

        for runtime, runtime_root_dir in BUILD_MAPPINGS.items():
            lambdas_path = resolve_lambda_path(
                project_path, runtime, runtime_root_dir
            )
            if os.path.exists(lambdas_path):
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
        lambda_names = []
        java_lambda_regex = re.compile(r'lambdaName\s*=\s*"(.+?)"')

        if not path.exists():
            return []

        if runtime == RUNTIME_JAVA:
            for java_file in path.rglob("*.java"):
                if not java_file.is_file():
                    continue
                try:
                    content = java_file.read_text(encoding='utf-8')
                    match = java_lambda_regex.search(content)
                    if match:
                        lambda_names.append(match.group(1))
                except Exception:
                    print(f"Couldn't read or parse Java file: {java_file.absolute()}", file=sys.stderr)
        else:
            for item in path.iterdir():
                if (item / LAMBDA_CONFIG_FILE).exists():
                    lambda_names.append(item.name)

        return lambda_names

    @staticmethod
    def _resolve_bpm_resources_from_path(path: Path, runtime: str) -> list:
        """
        Resolves a list of names bound to build project mapping dependent
        resources, retained inside a given path, based on a provided runtime.
        :parameter path: Path
        :parameter runtime: str
        :return: List[str]
        """

        _config_file_name_suffix = '_config.json'
        resources = []

        if not path.exists():
            return resources

        for item in path.iterdir():
            if not item.is_dir():
                continue
            for filename in item.iterdir():
                if filename.name.endswith(_config_file_name_suffix):
                    resources.append(filename.name)

        return resources
