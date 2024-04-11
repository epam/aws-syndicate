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
import re
import subprocess
import sys
import logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from signal import SIGINT
from threading import Thread
from time import time

import click
from click import BadParameter
from tqdm import tqdm

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.conf.processor import path_resolver
from syndicate.core.conf.validator import ConfigValidator, ALL_REGIONS
from syndicate.core.constants import (BUILD_META_FILE_NAME,
                                      DEFAULT_SEP, DATE_FORMAT_ISO_8601,
                                      CUSTOM_AUTHORIZER_KEY)
from syndicate.core.project_state.project_state import MODIFICATION_LOCK, \
    WARMUP_LOCK, ProjectState
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
            USER_LOG.error('An error occurred. See details in the log file')
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


def param_to_lower(ctx, param, value):
    if isinstance(value, tuple):
        return tuple([a_value.lower() for a_value in value])
    if isinstance(value, str):
        return value.lower()


def resolve_path_callback(ctx, param, value):
    if not value:
        raise BadParameter('Parameter is required')
    return path_resolver(value)


def generate_default_bundle_name(ctx, param, value):
    if value:
        return value
    from syndicate.core import CONFIG
    # regex to replace all special characters except dash, underscore and dot
    pattern = re.compile('[^0-9a-zA-Z.\-_]')
    project_path = CONFIG.project_path
    project_name = project_path.split("/")[-1]
    result_project_name = re.sub(pattern, '', project_name)
    date = datetime.now().strftime("%y%m%d.%H%M%S")
    bundle_name = f'{result_project_name}_{date}'
    if len(bundle_name) > 63:
        USER_LOG.warn(f'Bundle name \'{bundle_name}\' is too long. Trim it to '
                      f'the last 63 characters. Please rename project to '
                      f'shorter name to avoid this warning.')
        return bundle_name[-63:]
    return bundle_name


def resolve_default_bundle_name(command_name):
    from syndicate.core import PROJECT_STATE
    if command_name == 'clean':
        bundle_name = PROJECT_STATE.latest_deployed_bundle_name
    else:
        bundle_name = PROJECT_STATE.latest_bundle_name
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
    sync_project_state()
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
    from syndicate.core.build.helper import resolve_bundle_directory
    if not value:
        raise BadParameter('Parameter is required')
    bundle_path = resolve_bundle_directory(value)
    if not os.path.exists(bundle_path):
        os.makedirs(bundle_path)
    return value


def verify_bundle_callback(ctx, param, value):
    from syndicate.core.build.helper import resolve_bundle_directory
    bundle_path = resolve_bundle_directory(value)
    if not os.path.exists(bundle_path):
        raise click.BadParameter(
            "Bundle name does not exist. Please, invoke "
            "'syndicate assemble' command to create a bundle.")
    return value


def verify_meta_bundle_callback(ctx, param, value):
    from syndicate.core.build.helper import resolve_bundle_directory
    bundle_path = resolve_bundle_directory(value)
    build_meta_path = os.path.join(bundle_path, BUILD_META_FILE_NAME)
    if not os.path.exists(build_meta_path):
        raise click.BadParameter(
            "Bundle name is incorrect. {0} does not exist. Please, invoke "
            "'package_meta' command to create a file.".format(
                BUILD_META_FILE_NAME))
    return value


def resolve_and_verify_bundle_callback(ctx, param, value):
    if not value:
        _LOG.debug(f'{param.name} is not specified, latest build will be used')
        value = resolve_default_value(ctx, param, value)
        if not value:
            raise click.BadParameter(
                f'Couldn\'t resolve the parameter automatically. '
                f'Try to specify it manually'
            )
    return verify_meta_bundle_callback(ctx, param, value)


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
            try:
                func(*args, **kwargs)
            except Exception as e:
                _LOG.exception("Error occurred: %s", str(e))
                from syndicate.core import PROJECT_STATE
                PROJECT_STATE.release_lock(lock_type)
                sync_project_state()
                sys.exit(1)
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
            result_action_name = result.get('operation') if \
                isinstance(result, dict) else None
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
                    operation=result_action_name or action_name,
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


def string_to_upper_camel_case(s: str):
    temp = s.split('_')
    res = ''.join(ele.title() for ele in temp)
    return str(res)


def dict_keys_to_camel_case(d: dict):
    return _inner_dict_keys_to_camel_case(d, string_to_camel_case)


def dict_keys_to_upper_camel_case(d: dict):
    return _inner_dict_keys_to_camel_case(d, string_to_upper_camel_case)


def _inner_dict_keys_to_camel_case(d: dict, case_formatter):
    new_d = {}
    for key, value in d.items():
        if isinstance(value, (str, int, float)):
            new_d[case_formatter(key)] = value

        if isinstance(value, list):
            new_list = []
            for index, item in enumerate(value):
                if isinstance(item, (str, int, float)):
                    new_list.append(item)
                if isinstance(item, dict):
                    new_list.append(dict_keys_to_camel_case(item))
            new_d[case_formatter(key)] = new_list

        if isinstance(value, dict):
            new_d[case_formatter(key)] = dict_keys_to_camel_case(value)

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
                    new_list.append(dict_keys_to_capitalized_camel_case(item))
            new_d[string_to_capitalized_camel_case(key)] = new_list

        if isinstance(value, dict):
            new_d[string_to_capitalized_camel_case(key)] = \
                dict_keys_to_capitalized_camel_case(value)

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
        self.allowed_all = allowed_all

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


class DictParamType(click.types.StringParamType):
    name = 'dict'
    ITEMS_SEPARATOR = ','
    KEY_VALUE_SEPARATOR = ':'

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        _LOG.info(f'Stripping {value} from "{self.ITEMS_SEPARATOR}" a bit..')
        value = value[1:] if value.startswith(self.ITEMS_SEPARATOR) else value
        value = value[:-1] if value.endswith(self.ITEMS_SEPARATOR) else value
        result = {}
        _LOG.info(f'Converting: {value} to dict..')

        try:
            for item in value.split(self.ITEMS_SEPARATOR):
                k, v = item.split(self.KEY_VALUE_SEPARATOR)
                result[k] = v
        except ValueError as e:
            raise BadParameter(f'Wrong format: {value}. '
                               f'Must be key:value or key,value. '
                               f'\nError: {e.__str__()}')

        _LOG.info(f'Converted to such a dict: {result}')
        return result

    def get_metavar(self, param):
        return f'KEY{self.KEY_VALUE_SEPARATOR}VALUE1' \
               f'{self.ITEMS_SEPARATOR}KEY2{self.KEY_VALUE_SEPARATOR}VALUE2'


def check_bundle_bucket_name(ctx, param, value):
    try:
        from syndicate.core.resources.s3_resource import validate_bucket_name
        bucket_name = value
        if '/' in value:
            bucket_name = value.split('/', 1)[0]
        validate_bucket_name(bucket_name)
        return value
    except ValueError as e:
        raise BadParameter(e.__str__())


def check_prefix(ctx, param, value):
    extended_prefix = ctx.params.get('extended_prefix')
    if value:
        value = value.lower().strip()
        if extended_prefix:
            result = ConfigValidator.validate_extended_prefix(param.name,
                                                              value)
        else:
            result = ConfigValidator.validate_prefix_suffix(param.name, value)
        if result:
            raise BadParameter(result)
        return value


def check_suffix(ctx, param, value):
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


def check_lambda_name(value):
    """Validates lambda's name"""
    _LOG.info(f"Validating lambda name: '{value}'")
    invalid_character = re.search('[^0-9a-zA-Z\-\_]', value)
    error = None
    if not 3 <= len(value) <= 63:
        error = f'lambda name \'{value}\' length must be between 3 and 63 characters'
    elif invalid_character:
        error = f'lambda name \'{value}\' contains invalid characters: ' \
                f'{invalid_character.group()}'
    elif value.startswith('-'):
        error = f"lambda name '{value}' cannot start with '-'"
    elif value.endswith('-'):
        error = f"lambda name '{value}' cannot end with '-'"
    if error:
        _LOG.error(f"Lambda name validation error: {error}")
        raise ValueError(error)
    _LOG.info(f"Lambda name: '{value}' passed the validation")


def check_lambdas_names(ctx, param, value):
    """Applies lambda name validator for each lambda's name"""
    for lambda_name in value:
        try:
            check_lambda_name(lambda_name)
        except ValueError as e:
            raise click.BadParameter(e.__str__(), ctx, param)
    return value


def check_lambda_layer_name(ctr, param, value):
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-_]{0,63}$'
    errors = []
    if len(value) > 64:
        errors.append('The length of lambda layer name must be less or equal '
                      'to 64 character')
    if not value[0].isalpha():
        errors.append('The first character of the lambda layer name must be '
                      'a letter')
    if not re.match(pattern, value):
        errors.append('The lambda layer name must contain only lowercase '
                      'letters, numbers, underscores and hyphens')
    if errors:
        raise BadParameter(f'The lambda layer name is invalid. Details:\n'
                           f'{errors}')
    return value


def check_lambda_existence(ctr, param, value):
    from syndicate.core import PROJECT_STATE
    lambdas = PROJECT_STATE.lambdas
    for lambda_name in value:
        if lambda_name not in lambdas:
            raise BadParameter(f'Lambda with name \'{lambda_name}\' not found. '
                               f'Please check the lambda name and try again')
    return value


def handle_interruption(_num: SIGINT, _frame):
    """ Meant to handle interruption signal, by releasing any given lock """
    _naming, _lock_types = 'PROJECT_STATE', (MODIFICATION_LOCK, WARMUP_LOCK)
    if _num == SIGINT:
        from syndicate.core import PROJECT_STATE
        _state = PROJECT_STATE
        if isinstance(_state, ProjectState):
            _locked_type = next((each for each in _lock_types
                                 if not _state.is_lock_free(each)), None)
            if _locked_type:
                _LOG.warn(f'Releasing the project state lock {_locked_type},'
                          'due to user interruption.')
                _state.release_lock(_locked_type)
                sync_project_state()
    sys.exit(_num)


def check_lambda_state_consistency(objected_lambdas: list,
                                   subjected_lambdas: dict, runtime: str):
    from syndicate.core.groups import RUNTIME
    return next((True for each in objected_lambdas if subjected_lambdas.get(
        each, {}).get(RUNTIME) == runtime), False)


def delete_none(_dict):
    """Delete None values recursively"""
    if isinstance(_dict, dict):
        for key, value in list(_dict.items()):
            if isinstance(value, (list, dict, tuple, set)):
                _dict[key] = delete_none(value)
            elif value is None or key is None:
                del _dict[key]

    elif isinstance(_dict, (list, set, tuple)):
        _dict = type(_dict)(
            delete_none(item) for item in _dict if item is not None)
    return _dict


def without_zip_ext(name: str) -> str:
    _zip = '.zip'
    if name.endswith(_zip):
        name = name[:-len(_zip)]
    return name


def zip_ext(name: str) -> str:
    _zip = '.zip'
    if not name.endswith(_zip):
        name = name + _zip
    return name


def check_file_extension(ctx, param, value, extensions):
    for extension in extensions:
        if value.lower().endswith(extension):
            return value
    raise BadParameter(f'Only files with extensions {extensions} are '
                       f'supported.')


def validate_incompatible_options(ctx, param, value, incompatible_options):
    if value:
        conflict_options = [option for option in incompatible_options if
                            ctx.params.get(option)]
        if conflict_options:
            raise BadParameter(f'Parameter \'{param.name}\' is incompatible '
                               f'with {conflict_options}')
        return value


def validate_authorizer_name_option(ctx, param, value):
    if value:
        authorization_type = ctx.params.get('authorization_type')
        if not authorization_type:
            raise BadParameter(f'Parameter \'{param.name}\' can\'t be used '
                               f'without \'authorization_type\' parameter')
        if authorization_type != CUSTOM_AUTHORIZER_KEY:
            raise BadParameter(f'Parameter \'{param.name}\' can\'t be used '
                               f'with \'authorization_type\' '
                               f'\'{authorization_type}\'')
        return value


def set_debug_log_level(ctx, param, value):
    if value:
        loggers = [logging.getLogger(name) for name in
                   logging.root.manager.loggerDict if
                   name.startswith('syndicate') or
                   name.startswith('user-syndicate')]
        for logger in loggers:
            if not logger.isEnabledFor(logging.DEBUG):
                logger.setLevel(logging.DEBUG)
                if logger.name == 'syndicate':
                    logger.addHandler(logging.StreamHandler())
        _LOG.debug('The logs level was set to DEBUG')


def verbose_option(func):
    @click.option('--verbose', '-v', is_flag=True,
                  callback=set_debug_log_level, expose_value=False,
                  is_eager=True, help="Enable logging verbose mode.")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
