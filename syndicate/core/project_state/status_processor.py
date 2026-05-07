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
import json
import os
from datetime import datetime

from tabulate import tabulate

from syndicate.core.build.bundle_processor import load_latest_deploy_output
from syndicate.core.helper import strip_prefix_suffix
from syndicate.core.project_state.project_state import (
    OPERATION_LOCK_MAPPINGS, MODIFICATION_LOCK, WARMUP_LOCK,
    LOCK_LAST_MODIFICATION_DATE, LOCK_LOCKED_TILL)
from syndicate.core.project_state.sync_processor import sync_project_state
from syndicate.core.constants import (
    DATE_FORMAT_ISO_8601, MODIFICATION_OPS, DEPLOYED_MARKER, UNDEPLOYED_MARKER,
    RESOURCES_FILE_NAME
)

from syndicate.commons.log_helper import get_logger

_LOG = get_logger(__name__)

LOCKS = {
    MODIFICATION_LOCK: 'modification',
    WARMUP_LOCK: 'warmup'
}

LINE_SEP = os.linesep

SKIP_DIRS = {
    'venv', '.venv', '.git', 'node_modules', '.idea',
    '__pycache__', '.tox', '.eggs', 'dist', 'build', '.mypy_cache',
    '.pytest_cache', '.serverless', '.terraform'
}


# deployment_resources.json is the standard name


def project_state_status(category=None, deployed_only=False):
    sync_project_state()
    if category == 'events':
        return process_events_view()
    elif category == 'resources':
        return process_resources_view(deployed_only=deployed_only)
    else:
        return process_default_view()


def process_default_view():
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name
    events = PROJECT_STATE.events
    last_event = {}
    latest_operation = None
    is_locked = False
    if events:
        last_event = events[0]
        latest_operation = last_event.get('operation')
        lock_name = OPERATION_LOCK_MAPPINGS.get(latest_operation)
        is_locked = not PROJECT_STATE.is_lock_free(lock_name)

    state = 'Locked' if is_locked else 'Available'

    result = [
        f'Project: {project_name}',
        f'State: {state}',
        LINE_SEP + locks_summary(PROJECT_STATE)
    ]

    last_modification = PROJECT_STATE.latest_modification
    if last_modification and latest_operation not in MODIFICATION_OPS:
        operation = last_modification.get('operation')
        result.append(LINE_SEP + f'Latest modification: {operation}')
        modification_start_time = last_modification.get('time_start')
        modification_end_time = last_modification.get('time_end')
        data = [
            ['', 'Bundle name: ', last_modification.get('bundle_name')],
            ['', 'Deploy name: ', last_modification.get('deploy_name')],
            ['', 'Initiated by: ', last_modification.get('initiator')],
            ['', 'Started at: ', format_time(modification_start_time)],
            ['', 'Ended at: ', format_time(modification_end_time)],
            ['', 'Duration (sec): ',
             f"{last_modification.get('duration_sec')}"],
            ['', 'Status: ', f"{last_modification.get('status')}"],
        ]
        result.append(tabulate_data(data))

    if last_event:
        latest_operation = last_event.get('operation')
        result.append(LINE_SEP + f'Latest event: {latest_operation}')
        event_start_time = last_event.get('time_start')
        event_end_time = last_event.get('time_end')
        data = [
            ['', 'Bundle name: ', last_event.get('bundle_name')],
            ['', 'Initiated by: ', last_event.get('initiator')],
            ['', 'Started at: ', format_time(event_start_time)],
            ['', 'Ended at: ', format_time(event_end_time)],
            ['', 'Duration (sec): ', f"{last_event.get('duration_sec')}"],
            ['', 'Status: ', f"{last_event.get('status')}"],
        ]
        if last_event.get('deploy_name'):
            data.insert(1,
                        ['', 'Deploy name: ', last_event.get('deploy_name')])
        result.append(tabulate_data(data))

    result.append(LINE_SEP + 'Project resources:')
    all_resources = _collect_project_resources()
    deployed_resources = _collect_deployed_resource_names()

    if not all_resources:
        result.append(indent('No resources found in this project.'))
    else:
        grouped = _group_by_type(all_resources)
        headers = ['Type', 'Total', 'Deployed']
        summary_rows = []
        for resource_type in sorted(grouped.keys()):
            resources = grouped[resource_type]
            total = len(resources)
            deployed_count = sum(
                1 for name in resources
                if name in deployed_resources
            )
            summary_rows.append([resource_type, total, deployed_count])
        result.append(
            tabulate_data(data=summary_rows, headers=headers,
                          tablefmt='simple'))

        total_all = len(all_resources)
        deployed_all = sum(
            1 for name in all_resources
            if name in deployed_resources
        )
        result.append(
            f'{LINE_SEP}  Summary: {deployed_all}/{total_all} '
            f'resources deployed')

    return LINE_SEP + LINE_SEP.join(result)


def process_events_view():
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name
    result = ['Project: {}'.format(project_name),
              'Event logs:']
    events = PROJECT_STATE.events
    if events:
        headers = ['Operation', 'Started at', 'Duration (sec)',
                   'Initiator', 'Bundle', 'Deploy', 'Status']
        summaries = []
        for event in events:
            summaries.append([
                event.get('operation'),
                format_time(event.get('time_start')),
                event.get('duration_sec'),
                event.get('initiator'),
                event.get('bundle_name'),
                event.get('deploy_name'),
                event.get('status')
            ])
        result.append(tabulate_data(data=summaries, headers=headers,
                                    tablefmt='simple'))
    else:
        result.append('There are no events regarding this project.')
    return LINE_SEP + LINE_SEP.join(result)


def process_resources_view(deployed_only=False):
    from syndicate.core import PROJECT_STATE
    project_name = PROJECT_STATE.name

    result = [f'Project: {project_name}']

    all_resources = _collect_project_resources()
    deployed_resources = _collect_deployed_resource_names()

    if not all_resources:
        result.append('No resources found in this project.')
        return LINE_SEP + LINE_SEP.join(result)

    if deployed_only:
        result.append('Deployed resources:')
    else:
        result.append('Resources:')

    # Build flat table sorted by type, then by name
    headers = ['Type', 'Name', 'Status']
    rows = []
    total_count = 0
    deployed_count = 0

    for name, meta in sorted(all_resources.items(),
                              key=lambda x: (
                                  x[1].get('resource_type', 'unknown'),
                                  x[0])):
        resource_type = meta.get('resource_type', 'unknown')
        is_deployed = name in deployed_resources

        total_count += 1
        if is_deployed:
            deployed_count += 1

        if deployed_only and not is_deployed:
            continue

        status = DEPLOYED_MARKER if is_deployed else UNDEPLOYED_MARKER
        rows.append([resource_type, name, status])

    if rows:
        result.append(
            tabulate_data(data=rows, headers=headers, tablefmt='simple'))
    else:
        result.append(indent('No matching resources found.'))

    # Summary
    if deployed_only:
        result.append(
            LINE_SEP + f'Total deployed: {deployed_count} resources')
    else:
        result.append(
            LINE_SEP + f'Summary: {deployed_count}/{total_count} '
                       f'resources deployed')

    return LINE_SEP + LINE_SEP.join(result)

def _collect_project_resources():
    """
    Collects all project resources.
    Strategy:
      1. Fall back to scanning deployment_resources.json files
      2. Merge with lambdas from PROJECT_STATE
      3
    """
    resources = _scan_deployment_resources_files()
    resources = _merge_lambda_resources(resources)

    return resources


def _scan_deployment_resources_files():
    """Scan project directory for deployment_resources.json files,
    skipping large/irrelevant directories to improve performance."""
    resources = {}
    from syndicate.core import CONFIG
    project_path = CONFIG.project_path

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        if RESOURCES_FILE_NAME in files:
            filepath = os.path.join(str(root), RESOURCES_FILE_NAME)
            try:
                with open(filepath, 'r') as fh:
                    file_resources = json.load(fh)
                for name, meta in file_resources.items():
                    if isinstance(meta, dict) and meta.get(
                            'resource_type'):
                        resources[name] = meta
            except (json.JSONDecodeError, IOError) as e:
                _LOG.warning(f'Failed to read {filepath}: {e}')

    _LOG.debug(
        f'Scanned {len(resources)} resources from local files')
    return resources


def _merge_lambda_resources(resources):
    """Merge lambda definitions from PROJECT_STATE"""
    from syndicate.core import PROJECT_STATE
    lambdas = PROJECT_STATE.lambdas or {}
    for name, info in lambdas.items():
        if name not in resources:
            resources[name] = {
                'resource_type': 'lambda',
                **info
            }
        elif 'runtime' not in resources.get(name, {}):
            # Enrich existing lambda entry with runtime info
            resources[name]['runtime'] = info.get('runtime')
    return resources


def _collect_deployed_resource_names():
    """
    Returns a set containing BOTH resolved and stripped resource names
    from the latest deploy output, so comparison works regardless
    of whether project resources have prefix/suffix applied.
    """
    from syndicate.core import CONFIG

    try:
        is_regular, output = load_latest_deploy_output(failsafe=True)

        if is_regular is None:
            _LOG.debug('No deployment found in project state')
            return set()

        if not output:
            _LOG.debug('Deploy output is empty')
            return set()

        deployed_names = set()
        for arn, config in output.items():
            resource_name = config.get('resource_name')
            if resource_name:
                # Add resolved name (with prefix/suffix)
                deployed_names.add(resource_name)
                # Also add stripped name (without prefix/suffix)
                stripped = strip_prefix_suffix(resource_name)
                deployed_names.add(stripped)

        _LOG.debug(f'Found {len(deployed_names)} deployed resource '
                   f'name entries')
        return deployed_names

    except Exception as e:
        _LOG.warning(f'Failed to load deploy output: {e}')
        return set()


def _group_by_type(resources):
    """Groups {name: meta} dict by resource_type"""
    grouped = {}
    for name, meta in resources.items():
        rtype = meta.get('resource_type', 'unknown')
        if rtype not in grouped:
            grouped[rtype] = {}
        grouped[rtype][name] = meta
    return grouped


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
            state = 'Acquired' if lock_info.get(
                LOCK_LOCKED_TILL) else 'Released'
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
