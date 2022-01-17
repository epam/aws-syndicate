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
import logging
import getpass
import os
import sys
from pathlib import Path
from logging import DEBUG, Formatter, INFO, getLogger
from datetime import date

LOG_USER_HOME_FOLDER_NAME = '.syndicate_logs'
LOG_FOLDER_NAME = 'logs'
LOG_FILE_NAME = '%Y-%m-%d-syndicate.log'
LOG_NAME = 'syndicate'
LOG_LEVEL = (DEBUG
             if os.environ.get('SDCT_DEBUG', '').lower() == 'true'
             else INFO)
USER_NAME = getpass.getuser()
LOG_FORMAT_FOR_FILE = ('%(asctime)s [%(levelname)s] USER:{} %(filename)s:'
                       '%(lineno)d:%(funcName)s LOG: %(message)s'
                       .format(USER_NAME))


def get_project_log_file_path() -> str:
    """Returns the path to the file where logs will be saved.
    :rtype: str
    :returns: a path to the main log file
    """
    sdct_conf = os.getenv('SDCT_CONF')
    if sdct_conf:
        logs_path = os.path.join(sdct_conf, LOG_FOLDER_NAME)
    else:
        logs_path = os.path.join(Path.home(), LOG_USER_HOME_FOLDER_NAME)

    try:
        os.makedirs(logs_path, exist_ok=True)
    except OSError as e:
        print(f'Error while creating logs path: {e}', file=sys.stderr)

    today = date.today()
    log_file_path = os.path.join(logs_path, today.strftime(LOG_FILE_NAME))

    return log_file_path


log_file_path = get_project_log_file_path()

# formatter
formatter = Formatter(LOG_FORMAT_FOR_FILE)
# file output
file_handler = logging.FileHandler(filename=log_file_path)
file_handler.setFormatter(formatter)
# console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

user_logger = getLogger(f'user-{LOG_NAME}')
user_logger.addHandler(console_handler)
user_logger.addHandler(file_handler)

syndicate_logger = getLogger(LOG_NAME)
syndicate_logger.addHandler(file_handler)

if LOG_LEVEL == DEBUG:
    syndicate_logger.addHandler(console_handler)

logging.captureWarnings(True)


def get_logger(log_name, level=LOG_LEVEL):
    """
    :param level:   CRITICAL = 50
                    ERROR = 40
                    WARNING = 30
                    INFO = 20
                    DEBUG = 10
                    NOTSET = 0
    :type log_name: str
    :type level: int
    """
    module_logger = syndicate_logger.getChild(log_name)
    if level:
        module_logger.setLevel(level)
    return module_logger


def get_user_logger(level=LOG_LEVEL):
    """
    :param level:   CRITICAL = 50
                    ERROR = 40
                    WARNING = 30
                    INFO = 20
                    DEBUG = 10
                    NOTSET = 0
    :type level: int
    """
    module_logger = user_logger.getChild('child')
    if level:
        module_logger.setLevel(level)
    return module_logger
