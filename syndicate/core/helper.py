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
import collections
import concurrent.futures
import getpass
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from threading import Thread
from time import time

import click
from click import BadParameter
from tqdm import tqdm

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.conf.processor import path_resolver
from syndicate.core.conf.validator import ConfigValidator, ALL_REGIONS
from syndicate.core.constants import (ARTIFACTS_FOLDER, BUILD_META_FILE_NAME,
                                      DEFAULT_SEP, DATE_FORMAT_ISO_8601)
from syndicate.core.project_state.project_state import MODIFICATION_LOCK
from syndicate.core.project_state.sync_processor import sync_project_state

_LOG = get_logger('syndicate.core.helper')
USER_LOG = get_user_logger()

CONF_PATH = os.environ.get('SDCT_CONF')


def unpack_kwargs(handler_func):
    """ Decorator for unpack kwargs.

    :type handler_func: func
    :param handler_func: function which will be decorated
    """

    @wraps(handler_func)
    def wrapper(*kwargs):
        """ Wrapper func."""
        parameters = {}
        for i in kwargs:
            if type(i) is dict:
                parameters = i
        return handler_func(**parameters)

    return wrapper


def exit_on_exception(handler_func):
    """ Decorator to catch all exceptions and fail stage execution

    :type handler_func: func
    :param handler_func: function which will be decorated
    """

    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        """ Wrapper func."""
        try:
            return handler_func(*args, **kwargs)
        except Exception as e:
            _LOG.exception("Error occurred: %s", str(e))
            from syndicate.core import PROJECT_STATE
            PROJECT_STATE.release_lock(MODIFICATION_LOCK)
            sync_project_state()
            sys.exit(1)

    return wrapper


def prettify_json(obj):
    return json.dumps(obj, indent=4)


def cli_command(handler_func):
    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        status_code = handler_func(*args, **kwargs)
        if status_code != 0:
            _LOG.error('Execution is failed')
            sys.exit(1)

    return wrapper


@cli_command
def execute_command_by_path(command, path):
    return subprocess.call(command, shell=True, cwd=path)


@cli_command
def execute_command(command):
    return subprocess.call(command, shell=True)


def build_path(*paths):
    return DEFAULT_SEP.join(paths)


def _find_alias_and_replace(some_string):
    """ Find placeholder for alias in string. If found - replace with alias
    value.

    :type some_string: str
    """
    from syndicate.core import CONFIG
    first_index = some_string.index('${')
    second_index = some_string.index('}')
    alias_name = some_string[first_index + 2:second_index]
    res_alias = CONFIG.resolve_alias(alias_name)
    if not res_alias:
        raise AssertionError('Can not found alias for {0}'.format(alias_name))
    result = (
            some_string[:first_index] + res_alias + some_string[
                                                    second_index + 1:])
    return result


def resolve_aliases_for_string(string_value):
    """ Look for aliases in string.

    :type string_value: str
    """
    input_string = string_value
    try:
        if '${' in string_value:
            if string_value.count('${') == string_value.count('}'):
                while True:
                    input_string = _find_alias_and_replace(input_string)
            else:
                raise AssertionError('Broken alias in value: {0}.'.format(
                    string_value))
        return input_string
    except ValueError:
        return input_string

def check_required_param(ctx, param, value):
    if not value:
        raise BadParameter('Parameter is required')
    return value


def resolve_path_callback(ctx, param, value):
    if not value:
        raise BadParameter('Parameter is required')
    return path_resolver(value)


def generate_default_bundle_name(ctx, param, value):
    if value:
        return value
    from syndicate.core import CONFIG
    project_path = CONFIG.project_path
    project_name = project_path.split("/")[-1]
    date = datetime.now().strftime("%y%m%d.%H%M%S")
    return f'{project_name}_{date}'


def resolve_default_bundle_name(command_name):
    from syndicate.core import PROJECT_STATE
    if command_name == 'clean':
        bundle_name = PROJECT_STATE.latest_deployed_bundle_name
    else:
        bundle_name = PROJECT_STATE.latest_built_bundle_name
    if not bundle_name:
        click.echo('Property \'bundle\' is not specified and could '
                   'not be resolved due to absence of data about the '
                   'latest build operation')
        return
    return bundle_name


def resolve_default_deploy_name(command_name):
    from syndicate.core import PROJECT_STATE
    if command_name == 'clean':
        deploy_name = PROJECT_STATE.latest_deployed_deploy_name
    else:
        deploy_name = PROJECT_STATE.default_deploy_name

    return deploy_name


param_resolver_map = {
    'bundle_name': resolve_default_bundle_name,
    'deploy_name': resolve_default_deploy_name
}


def resolve_default_value(ctx, param, value):
    if value:
        return value
    command_name = ctx.info_name
    param_resolver = param_resolver_map.get(param.name)
    if not param_resolver:
        raise AssertionError(
            f'There is no resolver of default value '
            f'for param {param.name}')
    resolved_value = param_resolver(command_name=command_name)
    USER_LOG.info(f'Resolved value of {param.name}: {resolved_value}')
    return resolved_value


def create_bundle_callback(ctx, param, value):
    from syndicate.core import CONFIG
    bundle_path = os.path.join(CONFIG.project_path, ARTIFACTS_FOLDER, value)
    if not os.path.exists(bundle_path):
        os.makedirs(bundle_path)
    return value


def verify_bundle_callback(ctx, param, value):
    from syndicate.core import CONFIG
    bundle_path = os.path.join(CONFIG.project_path, ARTIFACTS_FOLDER, value)
    if not os.path.exists(bundle_path):
        raise AssertionError("Bundle name does not exist. Please, invoke "
                             "'build_artifacts' command to create a bundle.")
    return value


def verify_meta_bundle_callback(ctx, param, value):
    bundle_path = build_path(CONF_PATH, ARTIFACTS_FOLDER, value)
    build_meta_path = os.path.join(bundle_path, BUILD_META_FILE_NAME)
    if not os.path.exists(build_meta_path):
        raise AssertionError(
            "Bundle name is incorrect. {0} does not exist. Please, invoke "
            "'package_meta' command to create a file.".format(
                BUILD_META_FILE_NAME))
    return value


def write_content_to_file(file_path, file_name, obj):
    file_name = os.path.join(file_path, file_name)
    if os.path.exists(file_name):
        _LOG.warn('{0} already exists'.format(file_name))
    else:
        folder_path = Path(file_path)
        folder_path.mkdir(parents=True, exist_ok=True)
        meta_file = Path(file_name)
        meta_file.touch(exist_ok=True)
        with open(file_name, 'w+') as meta_file:
            json.dump(obj, meta_file)
        _LOG.info('{0} file was created.'.format(meta_file.name))


def sync_lock(lock_type):
    def real_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sync_project_state()
            from syndicate.core import PROJECT_STATE
            if PROJECT_STATE.is_lock_free(lock_type):
                PROJECT_STATE.acquire_lock(lock_type)
                sync_project_state()
            else:
                raise AssertionError(f'The project {lock_type} is locked.')
            func(*args, **kwargs)
            PROJECT_STATE.release_lock(lock_type)
            sync_project_state()
        return wrapper
    return real_wrapper


def timeit(action_name=None):
    def internal_timeit(func):
        @wraps(func)
        def timed(*args, **kwargs):
            ts = time()
            result = func(*args, **kwargs)
            te = time()
            _LOG.info('Stage %s, elapsed time: %s', func.__name__,
                      str(timedelta(seconds=te - ts)))
            if action_name:
                username = getpass.getuser()
                duration = round(te - ts, 3)
                start_date_formatted = datetime.fromtimestamp(ts) \
                    .strftime(DATE_FORMAT_ISO_8601)
                end_date_formatted = datetime.fromtimestamp(te) \
                    .strftime(DATE_FORMAT_ISO_8601)

                bundle_name = kwargs.get('bundle_name')
                deploy_name = kwargs.get('deploy_name')
                from syndicate.core import PROJECT_STATE
                PROJECT_STATE.log_execution_event(
                    operation=action_name,
                    initiator=username,
                    bundle_name=bundle_name,
                    deploy_name=deploy_name,
                    time_start=start_date_formatted,
                    time_end=end_date_formatted,
                    duration_sec=duration)
            return result

        return timed

    return internal_timeit


def execute_parallel_tasks(*fns):
    threads = []
    for fn in fns:
        t = Thread(target=fn)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def handle_futures_progress_bar(futures):
    kwargs = {
        'total': len(futures),
        'unit': 'nap',
        'leave': True
    }
    for _ in tqdm(concurrent.futures.as_completed(futures), **kwargs):
        pass


def string_to_camel_case(s: str):
    temp = s.split('_')
    res = temp[0] + ''.join(ele.title() for ele in temp[1:])
    return str(res)


def dict_keys_to_camel_case(d: dict):
    new_d = {}
    for key, value in d.items():
        if isinstance(value, (str, int)):
            new_d[string_to_camel_case(key)] = value

        if isinstance(value, list):
            new_list = []
            for index, item in enumerate(value):
                if isinstance(item, (str, int)):
                    new_list.append(item)
                if isinstance(item, dict):
                    new_list.append(dict_keys_to_camel_case(item))
            new_d[string_to_camel_case(key)] = new_list

        if isinstance(value, dict):
            new_d[string_to_camel_case(key)] = dict_keys_to_camel_case(value)

    return new_d


def string_to_capitalized_camel_case(s: str):
    temp = s.split('_')
    res = ''.join(ele.capitalize() for ele in temp)
    return res


def dict_keys_to_capitalized_camel_case(d: dict):
    new_d = {}
    for key, value in d.items():
        if isinstance(value, (str, int)):
            new_d[string_to_capitalized_camel_case(key)] = value

        if isinstance(value, list):
            new_list = []
            for index, item in enumerate(value):
                if isinstance(item, (str, int)):
                    new_list.append(item)
                if isinstance(item, dict):
                    new_list.append(dict_keys_to_camel_case(item))
            new_d[string_to_capitalized_camel_case(key)] = new_list

        if isinstance(value, dict):
            new_d[string_to_capitalized_camel_case(key)] = \
                dict_keys_to_camel_case(value)

    return new_d


class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands


class OptionRequiredIf(click.Option):
    def __init__(self, *args, **kwargs):
        self.required_if = kwargs.pop('required_if')
        if not self.required_if:
            raise AssertionError("'required_if' param must be specified")
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        is_current_present: bool = self.name in opts
        is_required_present: bool = self.required_if in opts
        if is_current_present ^ is_required_present:
            raise click.UsageError(f"options: '{self.name}' and "
                                   f"'{self.required_if}' "
                                   f"must be specified together")
        else:
            return super().handle_parse_result(ctx, opts, args)


class ValidRegionParamType(click.types.StringParamType):
    ALL_VALUE = 'ALL'
    name = 'region'

    def __init__(self, allowed_all=False):
        self.allowed_all=allowed_all

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if self.allowed_all and value.upper() == self.ALL_VALUE:
            _LOG.info("The value is 'ALL' and 'allowed_all=True', returning..")
            return value.lower()
        _LOG.info(f"Checking whether {value} is a valid region...")
        if value not in ALL_REGIONS:
            _LOG.error(f"Invalid region '{value}' was given")
            self.fail(f"Value '{value}' is not a valid region. Try one of "
                      f"these: {ALL_REGIONS}", param, ctx)
        _LOG.info(f"Value '{value}' is a valid region, returning..")
        return value

    def get_metavar(self, param):
        shorten_regions = [ALL_REGIONS[0], "...", ALL_REGIONS[-1]]
        if self.allowed_all:
            shorten_regions.insert(0, self.ALL_VALUE)
        return f"[{'|'.join(shorten_regions)}]"


def check_bundle_bucket_name(ctx, param, value):
    try:
        from syndicate.core.resources.s3_resource import validate_bucket_name
        validate_bucket_name(value)
        return value
    except ValueError as e:
        raise BadParameter(e.__str__())


def check_prefix_suffix_length(ctx, param, value):
    if value:
        value = value.lower().strip()
        result = ConfigValidator.validate_prefix_suffix(param.name, value)
        if result:
            raise BadParameter(result)
        return value

def resolve_project_path(ctx, param, value):
    from syndicate.core import CONFIG
    if not value:
        USER_LOG.info(f"Parameter: '{param.name}' wasn't specified. "
                      f"Getting automatically")
        value = CONFIG.project_path \
            if CONFIG and CONFIG.project_path else os.getcwd()
        USER_LOG.info(f"Path: '{value}' was assigned to the "
                      f"parameter: '{param.name}'")
    return value
