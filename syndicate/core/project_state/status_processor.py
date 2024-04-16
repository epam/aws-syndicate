"""
    Copyright 2021 EPAM Systems, Inc.

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
import os
from datetime import datetime

from tabulate import tabulate

from syndicate.core.project_state.project_state import (
    OPERATION_LOCK_MAPPINGS, MODIFICATION_LOCK, WARMUP_LOCK,
    LOCK_LAST_MODIFICATION_DATE, LOCK_LOCKED_TILL)
from syndicate.core.project_state.sync_processor import sync_project_state
from syndicate.core.constants import DATE_FORMAT_ISO_8601

LOCKS = {
    MODIFICATION_LOCK: 'modification',
    WARMUP_LOCK: 'warmup'
}

LINE_SEP = os.linesep


def project_state_status(category=None):
    sync_project_state()
    if category == 'events':
        return process_events_view()
    elif category == 'resources':
        return process_resources_view()
    else:
        return process_default_view()


def process_default_view():
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name
    events = PROJECT_STATE.events
    last_event = None
    is_locked = False
    if events:
        last_event = events[0]
        latest_operation = last_event.get('operation')
        lock_name = OPERATION_LOCK_MAPPINGS.get(latest_operation)
        is_locked = not PROJECT_STATE.is_lock_free(lock_name)
    state = 'Locked' if is_locked else 'Available'
    result = ['Project: {}'.format(project_name),
              'State: {}'.format(state)]
    last_modification = PROJECT_STATE.latest_modification
    if last_modification:
        operation = last_modification.get('operation')
        result.append(LINE_SEP + 'Latest modification: {}'.format(operation))
        modification_time = last_modification.get('time_start')
        data = [['', 'Bundle name: ', last_modification.get('bundle_name')],
                ['', 'Deploy name: ', last_modification.get('deploy_name')],
                ['', 'Initiated by: ', last_modification.get('initiator')],
                ['', 'Started at: ', format_time(modification_time)]]
        result.append(tabulate_data(data))

    result.append(LINE_SEP + locks_summary(PROJECT_STATE))

    if last_event:
        latest_operation = last_event.get('operation')
        result.append(LINE_SEP + 'Latest event: {}'.format(latest_operation))
        event_time = last_event.get('time_start')
        duration = last_event.get('duration_sec')
        data = [['', 'Bundle name: ', last_event.get('bundle_name')],
                ['', 'Initiated by: ', last_event.get('initiator')],
                ['', 'Started at: ', format_time(event_time)],
                ['', 'Duration (sec): ', "{:.3f}".format(duration)]]
        if last_event.get('deploy_name'):
            data.insert(1,
                        ['', 'Deploy name: ', last_event.get('deploy_name')])
        result.append(tabulate_data(data))
    lambdas = PROJECT_STATE.lambdas
    result.append(LINE_SEP + 'Project resources:')
    if lambdas:
        headers = ['Type', 'Quantity']
        resources = [['Lambda', len(lambdas)]]
        result.append(tabulate_data(data=resources, headers=headers,
                                    tablefmt='simple'))
    else:
        result.append(indent('There are no lambdas in this project.'))
    return LINE_SEP + LINE_SEP.join(result)


def process_events_view():
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name
    result = ['Project: {}'.format(project_name),
              'Event logs:']
    events = PROJECT_STATE.events
    if events:
        headers = ['Operation', 'Started at', 'Duration (sec)',
                   'Initiator', 'Bundle', 'Deploy']
        summaries = []
        for event in events:
            summaries.append([
                event.get('operation'),
                format_time(event.get('time_start')),
                event.get('duration_sec'),
                event.get('initiator'),
                event.get('bundle_name'),
                event.get('deploy_name'),
            ])
        result.append(tabulate_data(data=summaries, headers=headers,
                                    tablefmt='simple'))
    else:
        result.append('There are no events regarding this project.')
    return LINE_SEP + LINE_SEP.join(result)


def process_resources_view():
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name
    result = ['Project: {}'.format(project_name),
              'Lambda resources:']
    lambdas = PROJECT_STATE.lambdas
    if lambdas:
        headers = ['Name', 'Runtime']
        lambdas_data = []
        for lambda_name, lambda_info in lambdas.items():
            lambdas_data.append([lambda_name, lambda_info.get('runtime')])
        result.append(tabulate_data(data=lambdas_data, headers=headers,
                                    tablefmt='simple'))
    else:
        result.append(indent('There are no lambdas in this project.'))
    return LINE_SEP + LINE_SEP.join(result)


def locks_summary(project_state):
    result = ['Locks summary:']
    current_locks = project_state.locks
    all_locks = {
        MODIFICATION_LOCK: current_locks.get(MODIFICATION_LOCK),
        WARMUP_LOCK: current_locks.get(WARMUP_LOCK)
    }
    headers = ['Type', 'State', 'Last modification date', 'Locked till']
    locks_data = []
    for lock_name, lock_info in all_locks.items():
        display_name = LOCKS.get(lock_name)
        if lock_info:
            state = 'Acquired' if lock_info.get(LOCK_LOCKED_TILL) else 'Released'
            last_mod_date = lock_info.get(LOCK_LAST_MODIFICATION_DATE)
            last_mod_date = format_time(last_mod_date)
            locked_till_date = lock_info.get(LOCK_LOCKED_TILL)
            if locked_till_date:
                locked_till_date = format_time(locked_till_date)
            locks_data.append([
                display_name, state, last_mod_date, locked_till_date])
        else:
            locks_data.append([display_name, 'Released', None, None])
    result.append(tabulate_data(data=locks_data, headers=headers,
                                tablefmt='simple'))
    return LINE_SEP.join(result)


def tabulate_data(data, headers=(), tablefmt='plain'):
    return tabulate(tabular_data=data, tablefmt=tablefmt,
                    floatfmt='.3f', headers=headers, missingval='-')


def indent(line):
    return '    ' + line


def format_time(time_string):
    time = datetime.strptime(time_string, DATE_FORMAT_ISO_8601)
    return time.strftime('%Y-%m-%d %H:%M:%S')
