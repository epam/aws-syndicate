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
import traceback
from functools import reduce, wraps
from typing import Union, Any

from syndicate.commons.log_helper import get_logger, get_user_logger

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def deep_get(dct: dict, path: Union[list, tuple], default=None) -> Any:
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        path, dct)


def skip_if_error(error_patterns: Union[tuple[str, ...], None] = None):
    """ Decorator for scip on specified exceptions.

    :type error_patterns: tuple
    :param error_patterns: error patterns to match the error with
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            """ Wrapper func."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = str(e)
                skip_error = False

                if error_patterns is None:
                    skip_error = True
                else:
                    for pattern in error_patterns:
                        if pattern in error:
                            skip_error = True
                            break

                if skip_error:
                    USER_LOG.warning(f"The next error ignored: '{error}'")
                    _LOG.debug(f'Traceback:\n {traceback.format_exc()}')
                else:
                    raise

        return wrapper
    return decorator
