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
import datetime
import json
import os
import subprocess
import sys
from functools import wraps
from threading import Thread
from time import time

import click
from click import BadParameter
from tqdm import tqdm

from syndicate.commons.log_helper import get_logger
from syndicate.core.conf.processor import path_resolver
from syndicate.core.constants import (ARTIFACTS_FOLDER, BUILD_META_FILE_NAME,
                                      DEFAULT_SEP)

_LOG = get_logger('syndicate.core.helper')

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
        with open(file_name, 'w') as meta_file:
            json.dump(obj, meta_file)
        _LOG.info('{0} file was created.'.format(meta_file.name))


def timeit(handler_func):
    @wraps(handler_func)
    def timed(*args, **kwargs):
        ts = time()
        result = handler_func(*args, **kwargs)
        te = time()
        _LOG.info('Stage %s, elapsed time: %s', handler_func.__name__,
                  str(datetime.timedelta(seconds=te - ts)))
        return result

    return timed


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


class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands
