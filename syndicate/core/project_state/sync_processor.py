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
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.project_state.project_state import PROJECT_STATE_FILE
from syndicate.core.project_state.project_state import ProjectState

_LOG = get_logger('sync-processor')
USER_LOG = get_user_logger()


def sync_project_state():
    from syndicate.core import CONFIG, CONN, PROJECT_STATE
    from pathlib import PurePath
    bucket_name = CONFIG.deploy_target_bucket
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            PROJECT_STATE_FILE).as_posix()
    s3 = CONN.s3()
    if not s3.is_file_exists(bucket_name=bucket_name,
                             key=key_compound):
        _LOG.debug('Remote .syndicate file does not exists. Pushing...')
        PROJECT_STATE.save_to_remote()
        _LOG.debug('Push successful')

    else:
        _LOG.debug('Syncing with remote .syndicate file.')
        remote_project_state = ProjectState.get_remote()

        _LOG.debug('Actualizing the project state...')
        PROJECT_STATE.actualize_locks(remote_project_state)
        PROJECT_STATE.add_execution_events(remote_project_state.events)
        PROJECT_STATE.actualize_latest_deploy(remote_project_state)

        _LOG.debug('Saving a local .syndicate file.')
        PROJECT_STATE.save()

        _LOG.debug('Synced the .syndicate file. Pushing...')
        PROJECT_STATE.save_to_remote()
        _LOG.debug('Push successful')
        _LOG.debug('Remote .syndicate file pulled')
    _LOG.info('Project state file has been successfully synced')
