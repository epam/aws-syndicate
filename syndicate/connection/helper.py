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
from functools import wraps
from time import sleep

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger

_LOG = get_logger('syndicate.connection.helper')


DEFAULT_RETRY_TIMEOUT_SEC = 35
DEFAULT_RETRY_TIMEOUT_STEP = 3


def apply_methods_decorator(decorator):
    # todo after applying this decorator static methods do not work if they
    #  are invoked from an instance of a class instead of a class.
    # self.some_static_method(1, 2, 3)  # won't work
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def retry(retry_timeout=DEFAULT_RETRY_TIMEOUT_SEC,
          retry_timeout_step=DEFAULT_RETRY_TIMEOUT_STEP):
    """ Decorator for retry on specified exceptions.

    :type handler_func: func
    :param handler_func: function which will be decorated
    :param retry_timeout: retry timeout in seconds
    :param retry_timeout_step: step of the retry
    """

    def decorator(handler_func):
        @wraps(handler_func)
        def wrapper(*args, **kwargs):
            """ Wrapper func."""
            retry_exceptions = [
                'ThrottlingException',
                'LimitExceededException',
                'ProvisionedThroughputExceededException',
                'TooManyRequestsException',
                'ConflictException',
                'An error occurred (InvalidParameterValueException) when '
                'calling the CreateEventSourceMapping operation',
                'An error occurred (InvalidParameterValueException) when '
                'calling the UpdateEventSourceMapping operation',
                'An error occurred (InvalidParameterValueException) when '
                'calling the CreateCluster operation',
                'An error occurred (SubnetGroupInUseFault) when calling '
                'the DeleteSubnetGroup operation',
                'The role defined for the function cannot be assumed by Lambda',
                'An error occurred (ResourceConflictException) when calling'
                ' the AddPermission operation: The statement id',
                'NoSuchUpload',
                'Throttling',
                'Please add Lambda as a Trusted Entity',
                'UpdateFunctionConfiguration',
                'PutScalingPolicy',
                'RegisterScalableTarget',
                'TopicArn can not be None',
                'DeleteRole',
                'Max attempts exceeded',
                'UpdateGatewayResponse',
                'Cannot delete, found existing JobQueue relationship',
                'Cannot delete, resource is being modified',
            ]
            last_ex = None
            for each in range(1, retry_timeout, retry_timeout_step):
                try:
                    return handler_func(*args, **kwargs)
                except ClientError as e:
                    retry_flag = False
                    for exc in retry_exceptions:
                        if exc in str(e):
                            _LOG.warning(f'Retry on {handler_func.__name__}. '
                                         f'Error: {str(e)}')
                            _LOG.debug(
                                f'Parameters: {str(args)}, {str(kwargs)}')
                            # set to debug, we need it only in the logs file
                            _LOG.debug(
                                f'Traceback:\n {traceback.format_exc()}')
                            retry_flag = True
                    if not retry_flag:
                        _LOG.error(f'Error occurred: {e}')
                        _LOG.error(f'Traceback:\n {traceback.format_exc()}')
                        raise e
                    last_ex = e
                    sleep(each)

            if last_ex:
                raise Exception(
                    f"Maximum retries reached for function "
                    f"{handler_func.__name__} due to {type(last_ex).__name__}: "
                    f"{str(last_ex)}") from last_ex
        return wrapper
    return decorator
