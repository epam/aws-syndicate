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
import yaml

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.project_state.project_state import PROJECT_STATE_FILE

_LOG = get_logger('sync-processor')
USER_LOG = get_user_logger('sync-processor')


def sync_project_state():
    from syndicate.core import CONFIG, CONN, PROJECT_STATE
    bucket_name = CONFIG.deploy_target_bucket
    s3 = CONN.s3()
    if not s3.is_file_exists(bucket_name=bucket_name,
                             key=PROJECT_STATE_FILE):
        _LOG.debug('Remote .syndicate file does not exists. Pushing...')
        s3.put_object(file_obj=yaml.dump(PROJECT_STATE),
                      key=PROJECT_STATE_FILE,
                      bucket=bucket_name,
                      content_type='application/x-yaml')
        _LOG.debug('Push successful')

    else:
        remote_project_state = s3.load_file_body(bucket_name=bucket_name,
                                                 key=PROJECT_STATE_FILE)
        # todo sync remote .syndicate with local one
        # actualise locks state depending on last_modified_date
        # merge events, sort by time acsending, cut to 20 most recent events
        # flush to local dist
        # push to s3
        _LOG.debug('Remote .syndicate file pulled')
    USER_LOG.info('Project state file has been successfully synced')
