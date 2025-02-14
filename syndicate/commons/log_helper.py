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
import logging.config
import getpass
import os
import sys
from pathlib import Path
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from datetime import date

LOG_USER_HOME_FOLDER_NAME = '.syndicate_logs'
LOG_FOLDER_NAME = 'logs'
LOG_FILE_NAME = '%Y-%m-%d-syndicate.log'
LOG_NAME = 'syndicate'
USER_LOG_NAME = f'user-{LOG_NAME}'
CONSOLE_HANDLER = 'console_handler'
LOG_LEVEL = (DEBUG
             if os.environ.get('SDCT_DEBUG', '').lower() == 'true'
             else INFO)
USER_NAME = getpass.getuser()
LOG_FORMAT_FOR_FILE = (
    f'%(asctime)s [%(levelname)s] USER:{USER_NAME} '
    f'%(filename)s:%(lineno)d:%(funcName)s LOG: %(message)s'
)
LOG_FORMAT_FOR_CONSOLE = '[%(levelname)s] %(message)s'


class ConsoleLogFormatter(logging.Formatter):
    """Logging Formatter to add colors to console logs"""

    grey = '\x1b[0;37m'
    white = '\x1b[0;38m'
    yellow = '\x1b[0;33m'
    red = '\x1b[0;31m'
    reset = '\x1b[0m'
    format = LOG_FORMAT_FOR_CONSOLE

    FORMATS = {
        DEBUG: grey + format + reset,
        INFO: white + format + reset,
        WARNING: yellow + format + reset,
        ERROR: red + format + reset,
        CRITICAL: red + format + reset
    }

    def format(self, record: logging.LogRecord) -> str:
        log_format = self.FORMATS.get(record.levelno)
        console_formatter = logging.Formatter(log_format)
        return console_formatter.format(record)


def get_project_log_file_path() -> str:
    """Returns the path to the file where logs will be saved.
    :rtype: str
    :returns: a path to the main log file
    """
    sdct_conf = os.getenv('SDCT_CONF')
    if sdct_conf:
        logs_path = os.path.join(sdct_conf, LOG_FOLDER_NAME)
    else:
        logs_folder_path = os.environ.get('SDCT_LOGS') or Path.home()
        logs_path = os.path.join(logs_folder_path, LOG_USER_HOME_FOLDER_NAME)

    try:
        os.makedirs(logs_path, exist_ok=True)
    except OSError as e:
        print(f'Error while creating logs path: {e}', file=sys.stderr)

    today = date.today()
    log_file_path = os.path.join(logs_path, today.strftime(LOG_FILE_NAME))

    return log_file_path


log_file_path = get_project_log_file_path()

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file_formatter': {
            'format': LOG_FORMAT_FOR_FILE
        },
        'console_formatter': {
            '()': ConsoleLogFormatter
        }
    },
    'handlers': {
        'file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'file_formatter',
            'filename': log_file_path
        },
        CONSOLE_HANDLER: {
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        USER_LOG_NAME: {
            'level': LOG_LEVEL,
            'handlers': [
                CONSOLE_HANDLER,
                'file_handler'
            ]
        },
        LOG_NAME: {
            'level': LOG_LEVEL,
            'handlers': [
                'file_handler'
            ]
        }
    }
}

if LOG_LEVEL == DEBUG:
    logging_config['loggers'][LOG_NAME]['handlers'].append(
        CONSOLE_HANDLER
    )

logging.config.dictConfig(logging_config)

logging.captureWarnings(True)

user_logger = logging.getLogger(USER_LOG_NAME)

syndicate_logger = logging.getLogger(LOG_NAME)


def get_logger(log_name: str, level=LOG_LEVEL):
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
