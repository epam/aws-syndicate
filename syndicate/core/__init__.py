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

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection import ConnectionProvider
from syndicate.connection.sts_connection import STSConnection
from syndicate.core.conf.processor import ConfigHolder
from syndicate.core.resources.processors_mapping import ProcessorFacade
from syndicate.core.resources.resources_provider import ResourceProvider

_LOG = get_logger('deployment.__init__')

SESSION_TOKEN = 'aws_session_token'
SECRET_KEY = 'aws_secret_access_key'
ACCESS_KEY = 'aws_access_key_id'


def exception_handler(exception_type, exception, traceback):
    print(exception)


# sys.excepthook = exception_handler

# CONF VARS ===================================================================
CONF_PATH = os.environ.get('SDCT_CONF')
CONFIG = None
CONN = None
CREDENTIALS = None
RESOURCES_PROVIDER = None
PROCESSOR_FACADE = None


def _ready_to_assume():
    return CONFIG.access_role and CONFIG.aws_access_key_id and \
           CONFIG.aws_secret_access_key


def _ready_to_use_creds():
    return not CONFIG.access_role and CONFIG.aws_access_key_id and \
           CONFIG.aws_secret_access_key


def initialize_connection():
    global CONFIG
    global CONN
    global CONF_PATH
    global CREDENTIALS
    global RESOURCES_PROVIDER
    global PROCESSOR_FACADE

    CONFIG = ConfigHolder(CONF_PATH)
    sts = STSConnection(CONFIG.region, CONFIG.aws_access_key_id,
                        CONFIG.aws_secret_access_key)
    try:
        CREDENTIALS = {
            'region': CONFIG.region
        }
        if _ready_to_assume():
            _LOG.debug('Starting to assume role ...')
            # get CREDENTIALS for N hours
            temp_credentials = sts.get_temp_credentials(CONFIG.access_role,
                                                        CONFIG.account_id,
                                                        CONFIG.session_duration)
            _LOG.debug(f'Role {CONFIG.access_role} is assumed successfully'
                       f'for {CONFIG.session_duration} seconds')
            CREDENTIALS[ACCESS_KEY] = temp_credentials['AccessKeyId']
            CREDENTIALS[SECRET_KEY] = temp_credentials['SecretAccessKey']
            CREDENTIALS[SESSION_TOKEN] = temp_credentials['SessionToken']
        elif _ready_to_use_creds():
            _LOG.debug('Credentials access')
            CREDENTIALS[ACCESS_KEY] = CONFIG.aws_access_key_id
            CREDENTIALS[SECRET_KEY] = CONFIG.aws_secret_access_key
        CONN = ConnectionProvider(CREDENTIALS)
        RESOURCES_PROVIDER = ResourceProvider(config=CONFIG,
                                              credentials=CREDENTIALS,
                                              sts_conn=sts)
        PROCESSOR_FACADE = ProcessorFacade(
            resources_provider=RESOURCES_PROVIDER)
        _LOG.debug('aws-syndicate has been initialized')
    except ClientError:
        raise AssertionError('Cannot assume {0} role. '
                             'Please verify that you have configured '
                             'the role correctly.'.format(CONFIG.access_role))
