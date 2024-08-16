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
from logging import DEBUG
import threading
from functools import wraps
from pathlib import PurePath
import click

from syndicate.commons.log_helper import get_logger, get_user_logger

_LOG = get_logger('syndicate.core.decorators')
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
                      f'new one, use --replace_output flag.'
                if _LOG.level > DEBUG:
                    _LOG.warn(msg)
                    click.echo(msg)
                else:
                    USER_LOG.warn(msg)
                return
        return func(*args, **kwargs)

    return real_wrapper


def check_deploy_bucket_exists(func):
    @wraps(func)
    def real_wrapper(*args, **kwargs):
        from syndicate.core import CONN
        from syndicate.core import CONFIG
        if not CONN.s3().is_bucket_exists(CONFIG.deploy_target_bucket):
            click.echo(
                'Cannot execute command: deploy target bucket does not exist. '
                'Please create it before executing commands that require '
                'files to be uploaded to the bucket.')
            return
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
