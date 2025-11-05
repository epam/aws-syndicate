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
import concurrent.futures
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import logging
import traceback
import zipfile
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from signal import SIGINT
from threading import Thread
from time import time
from typing import Union

import click
from click import BadParameter, MissingParameter
from tqdm import tqdm

from syndicate.exceptions import ArtifactAssemblingError, \
    InternalError, ProjectStateError, InvalidValueError, \
    SyndicateBaseError
from syndicate.commons.log_helper import get_logger, get_user_logger, \
    LOG_NAME, USER_LOG_NAME
from syndicate.core.conf.processor import path_resolver
from syndicate.core.conf.validator import ConfigValidator, ALL_REGIONS
from syndicate.core.constants import (BUILD_META_FILE_NAME,
                                      DEFAULT_SEP, DATE_FORMAT_ISO_8601,
                                      CUSTOM_AUTHORIZER_KEY, OK_RETURN_CODE,
                                      ABORTED_RETURN_CODE, FAILED_RETURN_CODE,
                                      PROFILER_ACTION, UPDATE_ACTION,
                                      WARMUP_ACTION, DEFAULT_JSON_INDENT)
from syndicate.core.project_state.project_state import MODIFICATION_LOCK, \
    WARMUP_LOCK, ProjectState
from syndicate.core.project_state.sync_processor import sync_project_state

_LOG = get_logger(__name__)
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


def failed_status_code_on_exception(handler_func):
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
            if isinstance(e, BadParameter):
                message = f"{e.__class__.__name__} {e.message}"
            elif isinstance(e, SyndicateBaseError):
                message = f"{e.__class__.__name__} occurred: {str(e)}"
            else:
                message = (f'An unexpected error occurred: '
                           f'{e.__class__.__name__} {str(e)}')

            USER_LOG.error(message)
            _LOG.exception(traceback.format_exc())

            return FAILED_RETURN_CODE

    return wrapper


def prettify_json(obj):
    return json.dumps(obj, indent=DEFAULT_JSON_INDENT)


def execute_command_by_path(command, path, shell=True):
    result = subprocess.run(command, shell=shell, cwd=path,
                            capture_output=True, text=True)

    pretty_command = \
        ' '.join(command) if isinstance(command, list) else command
    if result.returncode != 0:
        msg = (f'While running the command "{pretty_command}" occurred an '
               f'error:\n"{result.stdout}\n{result.stderr}"')
        raise ArtifactAssemblingError(msg)
    _LOG.info(f'Running the command "{pretty_command}"\n{result.stdout}'
              f'\n{result.stderr}')


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
        raise InvalidValueError(f"Can not find alias for '{alias_name}'")
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
                raise InvalidValueError(
                    f"Broken alias in value: '{string_value}'."
                )
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
    if CONFIG is None:
        USER_LOG.error('Configuration is not initialized. '
                       'Please check your configuration.')
        sys.exit(ABORTED_RETURN_CODE)

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
    if command_name in (PROFILER_ACTION, WARMUP_ACTION):
        bundle_name = PROJECT_STATE.latest_deployed_bundle_name
    else:
        bundle_name = PROJECT_STATE.latest_bundle_name
    if not bundle_name:
        USER_LOG.error(
            'Property \'bundle\' could not be resolved from the syndicate '
            'project state file.'
        )
        return ABORTED_RETURN_CODE
    return bundle_name


def resolve_default_deploy_name(command_name):
    from syndicate.core import PROJECT_STATE
    if command_name in (PROFILER_ACTION, UPDATE_ACTION, WARMUP_ACTION):
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
        raise InternalError(
            f"There is no resolver of default value "
            f"for param {param.human_readable_name}")
    resolved_value = param_resolver(command_name=command_name)
    USER_LOG.info(
        f'Resolved value of {param.human_readable_name}: {resolved_value}')
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
        _LOG.debug(
            f'{param.human_readable_name} is not specified, latest build will '
            f'be used')
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
                raise ProjectStateError(
                    f"The project '{lock_type}' is locked. Run the command "
                    f"'syndicate status' for more details."
                )
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                _LOG.exception("Error occurred: %s", str(e))
                from syndicate.core import PROJECT_STATE
                PROJECT_STATE.release_lock(lock_type)
                sync_project_state()
                raise
            PROJECT_STATE.release_lock(lock_type)
            sync_project_state()
            return result

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
            if result_action_name:
                result = result.get('return_code', OK_RETURN_CODE)
            if action_name:
                username = getpass.getuser()
                duration = round(te - ts, 3)
                start_date_formatted = datetime.fromtimestamp(ts) \
                    .strftime(DATE_FORMAT_ISO_8601)
                end_date_formatted = datetime.fromtimestamp(te) \
                    .strftime(DATE_FORMAT_ISO_8601)

                bundle_name = kwargs.get('bundle_name')
                deploy_name = kwargs.get('deploy_name')
                rollback_on_error = kwargs.get('rollback_on_error')
                from syndicate.core import PROJECT_STATE
                PROJECT_STATE.log_execution_event(
                    operation=result_action_name or action_name,
                    initiator=username,
                    bundle_name=bundle_name,
                    deploy_name=deploy_name,
                    time_start=start_date_formatted,
                    time_end=end_date_formatted,
                    duration_sec=duration,
                    status=result,
                    rollback_on_error=rollback_on_error
                )
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


class OptionRequiredIf(click.Option):
    def __init__(self, *args, **kwargs):
        self.required_if = kwargs.pop('required_if')
        self.required_if_values = kwargs.pop('required_if_values', [])
        if not self.required_if:
            raise InternalError("'required_if' param must be specified")
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        is_current_present: bool = self.name in opts
        if self.required_if_values:
            is_required_ok: bool = \
                opts.get(self.required_if.replace('-','_')) in self.required_if_values
            message = (
                f"Option '{self.human_readable_name}' and '{self.required_if}' "
                f"must be specified together, and '{self.required_if}' must "
                f"have one of the next values {self.required_if_values}")
        else:
            is_required_ok: bool = self.required_if in opts
            message = (f"options: '{self.human_readable_name}' and "
                       f"'{self.required_if}' must be specified together")
        if is_current_present ^ is_required_ok:
            raise click.UsageError(message)
        else:
            return super().handle_parse_result(ctx, opts, args)


class MultiWordOption(click.Option):
    def __init__(self, *args, **kwargs):
        # Find name with "-" and add alias with "_"
        new_args = []

        for opt in args:
            alias_opts = []
            for alias in opt:
                if alias.startswith('--'):
                    underscored = alias[:2] + alias[2:].replace('-', '_')
                elif alias.startswith('-'):
                    underscored = alias[:1] + alias[1:].replace('-', '_')
                else:
                    underscored = alias.replace('-', '_')

                if underscored not in opt:
                    alias_opts.append(underscored)
            new_args.append(tuple(list(opt) + alias_opts))

        super().__init__(*new_args, **kwargs)

    def get_help_record(self, ctx):
        """
        Overrides the display of options in help, hiding aliases with
        underscores.
        """
        help_record = super().get_help_record(ctx)
        if help_record is None:
            return

        option_names = self.opts

        filtered = list(set([
            name.replace('_', '-') for name in option_names
        ]))

        if not self.is_flag and not self.count:
            filtered[-1] += f' {self.make_metavar()}'

        return ', '.join(filtered), help_record[1]

    @property
    def human_readable_name(self):
        """
        Overrides the human_readable_name to show the original name with dashes.
        """
        return self.name.replace('_', '-')


def combine_option_classes(*classes):
    """
    Combine multiple Click option classes into one.
    The order of classes matters, methods overlap in order of occurrence.
    """

    class CombinedOption(*classes, click.Option):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    return CombinedOption


class AliasedCommandsGroup(click.Group):
    """
    Custom Click Group to support command aliases.
    """

    def parse_args(self, ctx, args):
        current_cmd = self
        cmd_chain = []
        while args:
            next_arg = args[0]
            cmd = current_cmd.get_command(ctx, next_arg)
            if cmd is None:
                break
            cmd_chain.append(next_arg)
            args.pop(0)
            current_cmd = cmd
            if not isinstance(cmd, click.Group):
                break

        if isinstance(current_cmd, click.Group) and not args:
            sys.argv.append('--help')

        return super().parse_args(ctx, cmd_chain + args)

    def add_command(self, cmd, name=None):
        name = name or cmd.name
        super().add_command(cmd, name)

        alias_name = name.replace('-', '_')
        if alias_name != name and alias_name not in self.commands:
            self.commands[alias_name] = cmd

    def format_commands(self, ctx, formatter):
        """Format command list to hide aliases with underscore"""
        rows = []
        for subcommand in self.list_commands(ctx):
            command = self.get_command(ctx, subcommand)
            if command is None:
                continue
            help_text = command.get_short_help_str()

            if '-' in subcommand or '_' not in subcommand:
                rows.append((subcommand, help_text))
        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)

    def get_command(self, ctx, cmd_name):
        # get aliases
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        matches = [
            name for name, cmd in self.commands.items()
            if hasattr(cmd, 'aliases') and cmd_name in cmd.aliases
        ]
        if not matches:
            return None
        return self.commands[matches[0]]


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
                result[k.lstrip().rstrip()] = v.lstrip().rstrip()
        except ValueError as e:
            raise BadParameter(
                f'Wrong format: "{value}". '
                f'Must be "key:value" or "key1:value1,key2:value2". '
                f'\nError: {e.__str__()}')

        _LOG.info(f'Converted to such a dict: {result}')
        return result

    def get_metavar(self, param):
        return f'KEY1{self.KEY_VALUE_SEPARATOR}VALUE1' \
               f'{self.ITEMS_SEPARATOR}KEY2{self.KEY_VALUE_SEPARATOR}VALUE2'


class DeepDictParamType(click.types.StringParamType):
    name = 'deep-dict'
    ITEMS_SEPARATOR = ','
    SUB_KEY_VALUE_SEPARATOR = ':'
    MAIN_KEY_VALUE_SEPARATOR = ';'

    def convert(
            self,
            value: str,
            param: click.Parameter | None,
            ctx: click.Context | None,
    ) -> dict[str, dict[str, str]]:
        """
        Convert a string representation of nested key-value pairs into a
        dictionary of dictionaries

        **Example**::
            Input: 'volume;Name:DBStorage01,Environment:Prod'
            Output: {'volume': {'Name': 'DBStorage01', 'Environment': 'Prod'}}
        """
        value = super().convert(value, param, ctx)
        result = {}

        try:
            main_parts = value.split(self.MAIN_KEY_VALUE_SEPARATOR)
            if len(main_parts) != 2:
                raise InvalidValueError(
                    "Expected exactly one main key-value separator (';')"
                )
            main_key = main_parts[0].strip()
            sub_items = main_parts[1].strip()

            sub_dict = {}
            for item in sub_items.split(self.ITEMS_SEPARATOR):
                sub_parts = item.split(self.SUB_KEY_VALUE_SEPARATOR)
                if len(sub_parts) != 2:
                    raise InvalidValueError(
                        "Expected exactly one sub key-value separator (':')"
                    )
                sub_key = sub_parts[0].strip()
                sub_value = sub_parts[1].strip()
                sub_dict[sub_key] = sub_value

            result[main_key] = sub_dict
        except (ValueError, InvalidValueError) as e:
            raise BadParameter(
                f'Wrong format: "{value}". Expected format is: '
                f'"main_key1;sub_key1:val1,sub_key2:val2" or similar. '
                f'\nError: {str(e)}'
            )
        return result

    def get_metavar(self, param) -> str:
        return (
            f'MAIN_KEY1{self.MAIN_KEY_VALUE_SEPARATOR}'
            f'SUB_KEY1{self.SUB_KEY_VALUE_SEPARATOR}VALUE1{self.ITEMS_SEPARATOR}'
            f'SUB_KEY2{self.SUB_KEY_VALUE_SEPARATOR}VALUE2'
        )


def validate_bucket_name(ctx, param, value):
    try:
        from syndicate.core.resources.s3_resource import validate_bucket_name
        bucket_name = value
        if '/' in value:
            bucket_name = value.split('/', 1)[0]
        validate_bucket_name(bucket_name)
        return value
    except (ValueError, InvalidValueError) as e:
        raise BadParameter(e.__str__())


def check_prefix(ctx, param, value):
    extended_prefix = ctx.params.get('extended_prefix')
    if value:
        value = value.lower().strip()
        if extended_prefix:
            result = \
                ConfigValidator.validate_extended_prefix(
                    param.human_readable_name, value)
        else:
            result = \
                ConfigValidator.validate_prefix_suffix(
                    param.human_readable_name, value)
        if result:
            raise BadParameter(result)
        return value


def check_suffix(ctx, param, value):
    if value:
        value = value.lower().strip()
        result = \
            ConfigValidator.validate_prefix_suffix(param.human_readable_name,
                                                   value)
        if result:
            raise BadParameter(result)
        return value


def resolve_project_path(ctx, param, value):
    from syndicate.core import CONFIG
    if not value:
        USER_LOG.info(
            f"Parameter: '{param.human_readable_name}' wasn't specified. "
            f"Getting automatically")
        value = CONFIG.project_path \
            if CONFIG and CONFIG.project_path else os.getcwd()
        USER_LOG.info(f"Path: '{value}' was assigned to the "
                      f"parameter: '{param.human_readable_name}'")
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
        raise InvalidValueError(error)
    _LOG.info(f"Lambda name: '{value}' passed the validation")


def check_lambdas_names(ctx, param, value):
    """Applies lambda name validator for each lambda's name"""
    for lambda_name in value:
        try:
            check_lambda_name(lambda_name)
        except InvalidValueError as e:
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
            raise BadParameter(
                f'Lambda with name \'{lambda_name}\' not found. '
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


def is_zip_empty(zip_path):
    """Check if a ZIP file is empty"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            contents = zip_file.namelist()
            if not contents:
                return True
            else:
                return False
    except zipfile.BadZipFile:
        _LOG.info('The file is not a zip file or it is corrupted.')
        return True
    except FileNotFoundError:
        _LOG.info('The zip file does not exist.')
        return True


def check_file_extension(ctx, param, value, extensions):
    for extension in extensions:
        if value is None:
            return
        if value.lower().endswith(extension):
            return value
    raise BadParameter(f'Only files with extensions {extensions} are '
                       f'supported.')


def validate_incompatible_options(ctx, param, value, incompatible_options):
    if value:
        conflict_options = [
            option for option in incompatible_options if
            ctx.params.get(option.replace('-', '_')) or
            ctx.params.get(option)
        ]
        if conflict_options:
            raise BadParameter(
                f'Parameter \'{param.human_readable_name}\' is incompatible '
                f'with {conflict_options}'
            )
        return value


def validate_authorizer_name_option(ctx, param, value):
    if value:
        authorization_type = ctx.params.get('authorization_type')
        if not authorization_type:
            raise BadParameter(
                f'Parameter \'{param.human_readable_name}\' can\'t be used '
                f'without \'authorization-type\' parameter')
        if authorization_type != CUSTOM_AUTHORIZER_KEY:
            raise BadParameter(
                f"Parameter '{param.human_readable_name}' can't be used "
                f"with 'authorization_type' '{authorization_type}")
        return value


def validate_api_gw_path(ctx, param, value):
    pattern = (
        r'^/(?:([a-zA-Z0-9-._~]+|\{[a-zA-Z0-9-._~]+\})/)*([a-zA-Z0-9-._~]+|'
        r'\{[a-zA-Z0-9-._~]+\}|\{proxy\+\})$')
    _LOG.debug(
        f"The parameter '--{param.human_readable_name}' value is '{value}'")
    if os.name == 'nt' and Path(value).is_absolute():
        raise BadParameter(
            f"Your terminal resolves the parameter "
            f"'--{param.human_readable_name}' value as a filesystem path. "
            f"Please pass the parameter '--{param.human_readable_name}' "
            f"value without starting slash ('/')")
    if not value.startswith('/'):
        value = '/' + value
    if not re.match(pattern, value):
        raise BadParameter(
            f"'{value}'. "
            f"A valid API gateway path must begin with a '/' and can contain "
            f"alphanumeric characters, hyphens, periods, underscores or "
            "dynamic parameters wrapped in '{}'. "
        )
    return value


def check_tags(ctx, param, value):
    if value:
        errors = validate_tags(param.human_readable_name, value)
        if errors:
            raise BadParameter(errors)
        return value


def validate_tags(key_name, tags_dict):
    return ConfigValidator.validate_tags(key_name, tags_dict)


def set_debug_log_level(ctx, param, value):
    if value:
        loggers = [logging.getLogger(name) for name in
                   logging.root.manager.loggerDict if
                   name.startswith(LOG_NAME) or
                   name.startswith(USER_LOG_NAME)]

        console_handler = logging.getLogger(USER_LOG_NAME).handlers[0]

        for logger in loggers:
            if not logger.isEnabledFor(logging.DEBUG):
                logger.setLevel(logging.DEBUG)
                if logger.name == LOG_NAME:
                    logger.addHandler(console_handler)
        _LOG.debug('The logs level was set to DEBUG')


def verbose_option(func):
    @click.option('--verbose', '-v', is_flag=True,
                  callback=set_debug_log_level, expose_value=False,
                  is_eager=True, help="Enable logging verbose mode.")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def compute_file_hash(file_path: Union[str, Path],
                      algorithm: str = 'sha256') -> str:
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def resolve_deploy_target_bucket_param(ctx, param, value):
    if bundle_bucket_name := ctx.params.get('bundle_bucket_name'):
        USER_LOG.warn(
            "The parameter '--bundle-bucket-name' is deprecated! "
            "It is highly recommended to use '--deploy-target-bucket' instead."
        )

    bucket_name = value or bundle_bucket_name
    if not bucket_name:
        raise MissingParameter()

    return validate_bucket_name(ctx, param, bucket_name)


def are_resource_types_valid(param_name: str,
                             types: list[str] | None,
                             allowed_types: list[str]) -> bool:
    """
    Validate incoming from click AWS resource types
    """
    if not types:
        return True

    invalid_types = [t for t in types if
                     t not in allowed_types]
    if invalid_types:
        USER_LOG.error(
            f"Invalid resource type(s) in `{param_name}` "
            f"parameter: {', '.join(invalid_types)}. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        return False
    return True


def strip_prefix_suffix(res_name: str) -> str:
    """
    Strips the resource prefix and suffix if it is present.
    """
    from syndicate.core import CONFIG
    if CONFIG.resources_prefix and res_name.startswith(CONFIG.resources_prefix):
        res_name = res_name[len(CONFIG.resources_prefix):]
    if CONFIG.resources_suffix and res_name.endswith(CONFIG.resources_suffix):
        res_name = res_name[:-len(CONFIG.resources_suffix)]
    return res_name
