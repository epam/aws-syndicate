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
import os
import sys

from botocore.exceptions import ClientError
from botocore.vendored.requests.packages import urllib3

from syndicate.commons.log_helper import get_logger
from syndicate.connection import ConnectionProvider
from syndicate.connection.sts_connection import STSConnection
from syndicate.core.conf.config_holder import ConfigHolder

_LOG = get_logger('deployment.__init__')

S3_PATH_NAME = 's3_path'
SESSION_TOKEN = 'aws_session_token'
SECRET_KEY = 'aws_secret_access_key'
ACCESS_KEY = 'aws_access_key_id'


def exception_handler(exception_type, exception, traceback):
    print exception


sys.excepthook = exception_handler

# suppress botocore warnings
urllib3.disable_warnings()

try:
    CONF_PATH = os.environ['SDCT_CONF']
except KeyError:
    raise AssertionError('Environment variable SDCT_CONF is not set! '
                         'Please verify that you configured '
                         'framework correctly.')

# CONF VARS ===================================================================
CONFIG = ConfigHolder(CONF_PATH)

sts = STSConnection(CONFIG.region, CONFIG.aws_access_key_id,
                    CONFIG.aws_secret_access_key)


def _ready_to_assume():
    return CONFIG.access_role and CONFIG.aws_access_key_id and \
           CONFIG.aws_secret_access_key


def _ready_to_use_creds():
    return not CONFIG.access_role and CONFIG.aws_access_key_id and \
           CONFIG.aws_secret_access_key


try:
    CREDENTIALS = {
        'region': CONFIG.region
    }
    if _ready_to_assume():
        _LOG.debug('Starting to assume role ...')
        # get credentials for 12 hours
        temp_credentials = sts.get_temp_credentials(CONFIG.access_role,
                                                    CONFIG.account_id,
                                                    43200)
        _LOG.debug('Role %s is assumed successfully' % CONFIG.access_role)
        CREDENTIALS[ACCESS_KEY] = temp_credentials['AccessKeyId']
        CREDENTIALS[SECRET_KEY] = temp_credentials['SecretAccessKey']
        CREDENTIALS[SESSION_TOKEN] = temp_credentials['SessionToken']
    elif _ready_to_use_creds():
        _LOG.debug('Credentials access')
        CREDENTIALS[ACCESS_KEY] = CONFIG.aws_access_key_id
        CREDENTIALS[SECRET_KEY] = CONFIG.aws_secret_access_key
    CONN = ConnectionProvider(CREDENTIALS)
except ClientError:
    raise AssertionError('Cannot assume %s role. Please verify '
                         'that you have configured the role correctly.',
                         CONFIG.access_role)
