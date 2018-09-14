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
from functools import wraps
from time import sleep

from botocore.exceptions import ClientError
from commons.log_helper import get_logger

_LOG = get_logger('aws_connection.helper')


def apply_methods_decorator(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def retry(handler_func):
    """ Decorator for retry on specified exceptions.

    :type handler_func: func
    :param handler_func: function which will be decorated
    """

    # TODO check if it is possible to use it like this: @retry(on='blahblah')
    @wraps(handler_func)
    def wrapper(*args, **kwargs):
        """ Wrapper func."""
        retry_exceptions = [
            'ThrottlingException',
            'LimitExceededException',
            'ProvisionedThroughputExceededException',
            'TooManyRequestsException',
            'ConflictException',
            'The role defined for the function cannot be assumed by Lambda.',
            'An error occurred (InvalidParameterValueException) when calling'
            'CreateEventSourceMapping operation',
            'An error occurred (ResourceConflictException) when calling'
            ' the AddPermission operation: The statement id',
            'NoSuchUpload',
            'Throttling',
            'Reason: Adding cross-region target is not permitted',
            'Please add Lambda as a Trusted Entity',
            'UpdateFunctionConfiguration',
            'PutScalingPolicy',
            'RegisterScalableTarget',
            'TopicArn can not be None',
            '"message":"Too Many Requests"',
            'request PATCH https://apigateway',
            'CreateFunction',
            'DeleteRole']
        for each in xrange(1, 10, 3):
            try:
                return handler_func(*args, **kwargs)
            except ClientError as e:
                retry_flag = False
                for exc in retry_exceptions:
                    if exc in e.message:
                        _LOG.debug(
                            'Retry on {0}.'.format(handler_func.__name__))
                        retry_flag = True
                if not retry_flag:
                    raise e
                sleep(each)

    return wrapper
