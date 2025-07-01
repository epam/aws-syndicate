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
import sys
import traceback
import threading
from functools import wraps
from pathlib import PurePath

import click
from click import BadParameter

from syndicate.exceptions import SyndicateBaseError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import (ABORTED_RETURN_CODE, OK_RETURN_CODE,
                                      FAILED_RETURN_CODE)

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()

lock = threading.Lock()


def check_deploy_name_for_duplicates(func):
    """
    Checks whether output file with specified name already exists.
    Everywhere this decorator is used the following
    :param func:
    :return:
    """

    @wraps(func)
    def real_wrapper(*args, **kwargs):
        from syndicate.core import CONN
        from syndicate.core import CONFIG
        deploy_name = kwargs.get('deploy_name')
        bundle_name = kwargs.get('bundle_name')
        replace_output = kwargs.get('replace_output')
        if deploy_name and bundle_name and not replace_output:
            output_file_name = f'{bundle_name}/outputs/{deploy_name}.json'

            key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                                    output_file_name).as_posix()
            exists = CONN.s3().is_file_exists(CONFIG.deploy_target_bucket,
                                              key=key_compound)
            if exists:
                msg = f'Output file already exists with name ' \
                      f'{output_file_name}. If it should be replaced with ' \
                      f'new one, use --replace-output flag.'
                USER_LOG.error(msg)
                return ABORTED_RETURN_CODE
        return func(*args, **kwargs)

    return real_wrapper


def check_deploy_bucket_exists(func):
    @wraps(func)
    def real_wrapper(*args, **kwargs):
        from syndicate.core import CONN
        from syndicate.core import CONFIG
        if not CONN.s3().is_bucket_exists(CONFIG.deploy_target_bucket):
            USER_LOG.error(
                'Cannot execute command: deploy target bucket does not exist. '
                'Please create it before executing commands that require '
                'files to be uploaded to the bucket.')
            return ABORTED_RETURN_CODE
        return func(*args, **kwargs)

    return real_wrapper


def threading_lock(func):
    """ Synchronize access to a function with a threading lock
    to avoid race condition."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with lock:
            _LOG.info('Lock acquired')
            result = func(*args, **kwargs)
        _LOG.info('Lock released')
        return result

    return wrapper


def check_bundle_deploy_names_for_existence(check_deploy_existence=False):
    def internal_check(func):
        @wraps(func)
        def real_wrapper(*args, **kwargs):
            from syndicate.core.build.bundle_processor import if_bundle_exist
            from syndicate.core.build.deployment_processor import is_deploy_exist

            deploy_name = kwargs.get('deploy_name')
            bundle_name = kwargs.get('bundle_name')
            if not bundle_name:
                USER_LOG.error(f'The bundle name is undefined or invalid, '
                               f'please verify it and try again.')
                return ABORTED_RETURN_CODE
            if not deploy_name:
                USER_LOG.error(f'The deploy name is undefined or invalid, '
                               f'please verify it and try again.')
                return ABORTED_RETURN_CODE
            if not if_bundle_exist(bundle_name=bundle_name):
                USER_LOG.error(
                    f'The bundle name \'{bundle_name}\' does not exist '
                    f'in deploy bucket. Please verify the bundle name '
                    f'and try again.')
                return ABORTED_RETURN_CODE
            if check_deploy_existence and not is_deploy_exist(
                    bundle_name=bundle_name, deploy_name=deploy_name):
                USER_LOG.error(
                    f'The deploy name \'{deploy_name}\' is invalid. '
                    f'Please verify the deploy name and try again.')
                return ABORTED_RETURN_CODE
            return func(*args, **kwargs)
        return real_wrapper
    return internal_check


def return_code_manager(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return_code = func(*args, **kwargs)
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

            sys.exit(FAILED_RETURN_CODE)
        if return_code is not None and return_code != OK_RETURN_CODE:
            sys.exit(return_code)

        return return_code
    return wrapper


def tags_to_context(func):
    """
    Decorator to load resource tags and output from the latest deploy
    to click context
    """

    @click.pass_context
    @wraps(func)
    def wrapper(ctx, *args, **kwargs):
        from syndicate.core import PROJECT_STATE, RESOURCES_PROVIDER
        from syndicate.core.build.bundle_processor import load_deploy_output
        if PROJECT_STATE is None or not PROJECT_STATE.latest_deploy:
            USER_LOG.error(
                'Project state is not found/not initialized. '
                'Please check your configuration.'
            )
            sys.exit(FAILED_RETURN_CODE)

        deploy_name = PROJECT_STATE.latest_deploy.get('deploy_name')
        bundle_name = PROJECT_STATE.latest_deploy.get('bundle_name')
        output = load_deploy_output(bundle_name, deploy_name)

        ctx.ensure_object(dict)
        ctx.obj['output'] = output
        ctx.obj['tags_resource'] = RESOURCES_PROVIDER.tags_api()

        return_code = func(*args, **kwargs)
        return return_code
    return wrapper
