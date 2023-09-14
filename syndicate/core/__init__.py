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
import re
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection import ConnectionProvider
from syndicate.connection.sts_connection import STSConnection
from syndicate.core.conf.processor import ConfigHolder
from syndicate.core.project_state.project_state import ProjectState
from syndicate.core.resources.processors_mapping import ProcessorFacade
from syndicate.core.resources.resources_provider import ResourceProvider
from syndicate.core.conf.bucket_view import URIBucketView, RegexViewDigest, \
    NAMED_S3_URI_PATTERN, S3_PATTERN_GROUP_NAMES
from syndicate.core.helper import handle_interruption

_LOG = get_logger('deployment.__init__')
USER_LOG = get_user_logger()

SESSION_TOKEN = 'aws_session_token'
SECRET_KEY = 'aws_secret_access_key'
ACCESS_KEY = 'aws_access_key_id'

CONFIRMATION_ANSWERS = ['y', 'yes']

# if temporary credentials will be expired in less than N minutes,
# syndicate will regenerate temp credentials instead of using old ones
CREDENTIALS_EXPIRATION_THRESHOLD_MIN = 15


def exception_handler(exception_type, exception, traceback):
    print(exception)


# sys.excepthook = exception_handler

# CONF VARS ===================================================================
CONF_PATH = os.environ.get('SDCT_CONF')
CONFIG: ConfigHolder = None
CONN = None
CREDENTIALS = None
RESOURCES_PROVIDER = None
PROCESSOR_FACADE = None
PROJECT_STATE: ProjectState = None


def _ready_to_assume():
    return CONFIG.access_role and not CONFIG.use_temp_creds


def _ready_to_use_creds():
    return not CONFIG.access_role and CONFIG.aws_access_key_id and \
           CONFIG.aws_secret_access_key and not CONFIG.use_temp_creds


def _ready_to_use_provided_temp_creds():
    has_temporary_creds_set = CONFIG.temp_aws_access_key_id \
                              and CONFIG.temp_aws_secret_access_key \
                              and CONFIG.temp_aws_session_token \
                              and CONFIG.expiration

    credentials_valid = validate_temp_credentials(
        aws_access_key_id=CONFIG.temp_aws_access_key_id,
        aws_secret_access_key=CONFIG.temp_aws_secret_access_key,
        aws_session_token=CONFIG.temp_aws_session_token,
        expiration=CONFIG.expiration
    )

    return has_temporary_creds_set and credentials_valid


def _ready_to_generate_temp_creds():
    return not CONFIG.access_role and CONFIG.use_temp_creds


def initialize_connection():
    global CONFIG
    global CONN
    global CONF_PATH
    global CREDENTIALS
    global RESOURCES_PROVIDER
    global PROCESSOR_FACADE

    regex_digest = RegexViewDigest()
    regex_digest.expression = NAMED_S3_URI_PATTERN
    regex_digest.groups = S3_PATTERN_GROUP_NAMES
    uri_bucket_view = URIBucketView()
    uri_bucket_view.digest = regex_digest

    CONFIG = ConfigHolder(CONF_PATH)
    CONFIG.deploy_target_bucket_view = uri_bucket_view
    sts = STSConnection(CONFIG.region, CONFIG.aws_access_key_id,
                        CONFIG.aws_secret_access_key, CONFIG.aws_session_token)
    try:
        CREDENTIALS = {
            'region': CONFIG.region
        }
        if _ready_to_use_provided_temp_creds():
            _LOG.debug(f'Going to use previously generated temporary '
                       f'credentials')
            CREDENTIALS[ACCESS_KEY] = CONFIG.temp_aws_access_key_id
            CREDENTIALS[SECRET_KEY] = CONFIG.temp_aws_secret_access_key
            CREDENTIALS[SESSION_TOKEN] = CONFIG.temp_aws_session_token
        elif _ready_to_assume():
            _LOG.debug('Starting to assume role ...')
            # get CREDENTIALS for N hours

            token_code = prompt_mfa_code() if CONFIG.serial_number else None
            temp_credentials = sts.get_temp_credentials(
                role_arn=CONFIG.access_role,
                acc_id=CONFIG.account_id,
                duration=CONFIG.session_duration,
                serial_number=CONFIG.serial_number,
                token_code=token_code
            )
            _LOG.debug(f'Role {CONFIG.access_role} is assumed successfully'
                       f'for {CONFIG.session_duration} seconds')
            CREDENTIALS[ACCESS_KEY] = temp_credentials['AccessKeyId']
            CREDENTIALS[SECRET_KEY] = temp_credentials['SecretAccessKey']
            CREDENTIALS[SESSION_TOKEN] = temp_credentials['SessionToken']
            _LOG.debug(f'Temporary credentials have been successfully '
                       f'generated by assuming the role {CONFIG.access_role}, '
                       f'saving to config.')
            CONFIG.set_temp_credentials_to_config(
                temp_aws_access_key_id=temp_credentials['AccessKeyId'],
                temp_aws_secret_access_key=temp_credentials['SecretAccessKey'],
                temp_aws_session_token=temp_credentials['SessionToken'],
                expiration=temp_credentials['Expiration']
            )
        elif _ready_to_generate_temp_creds():
            _LOG.debug(f'Going to generate new temporary credentials')

            token_code = None
            if CONFIG.serial_number:
                token_code = prompt_mfa_code()
            temp_credentials = sts.get_session_token(
                duration=CONFIG.session_duration,
                serial_number=CONFIG.serial_number,
                token_code=token_code
            )
            CREDENTIALS[ACCESS_KEY] = temp_credentials['AccessKeyId']
            CREDENTIALS[SECRET_KEY] = temp_credentials['SecretAccessKey']
            CREDENTIALS[SESSION_TOKEN] = temp_credentials['SessionToken']
            _LOG.debug(f'Temporary credentials have been successfully '
                       f'generated, saving to config.')
            CONFIG.set_temp_credentials_to_config(
                temp_aws_access_key_id=temp_credentials['AccessKeyId'],
                temp_aws_secret_access_key=temp_credentials['SecretAccessKey'],
                temp_aws_session_token=temp_credentials['SessionToken'],
                expiration=temp_credentials['Expiration']
            )
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
    except ClientError as e:
        message = f'An unexpected error has occurred trying to ' \
                  f'init connection: {e}'
        _LOG.error(message)
        raise AssertionError(message)


def initialize_project_state():
    from syndicate.core.project_state.sync_processor import sync_project_state
    global PROJECT_STATE
    if not ProjectState.check_if_project_state_exists(CONFIG.project_path):
        USER_LOG.warn("\033[93mConfig is set and generated but project "
                      "state does not exist, seems that you've come from the "
                      "previous version.\033[0m")
        USER_LOG.warn("\033[93mGenerating project state file "
                      "(.syndicate) from the existing structure..."
                      "\033[0m")
        PROJECT_STATE = ProjectState.build_from_structure(CONFIG)
    else:
        PROJECT_STATE = ProjectState(project_path=CONFIG.project_path)


def validate_temp_credentials(aws_access_key_id, aws_secret_access_key,
                              aws_session_token, expiration):
    if not all((aws_access_key_id, aws_secret_access_key,
                aws_session_token, expiration)):
        return False
    if not isinstance(expiration, datetime):
        expiration = datetime.fromisoformat(expiration)
    expiration_datetime = expiration - timedelta(
        minutes=CREDENTIALS_EXPIRATION_THRESHOLD_MIN)
    now_datetime = datetime.now(timezone.utc)

    return expiration_datetime > now_datetime


def prompt_mfa_code():
    mfa_code = input('Please enter your MFA code to generate '
                     'temp credentials: ')
    while 1:
        if len(mfa_code) == 6 and re.match('[0-9]{6}', mfa_code):
            break
        mfa_code = input(f'Token code must consist of 6 numbers. '
                         f'Try again: ')
    return mfa_code


def initialize_signal_handling():
    from signal import SIGINT, signal
    signal(SIGINT, handle_interruption)
