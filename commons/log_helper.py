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
from logging import DEBUG, Formatter, INFO, getLogger

# file output
file_handler = logging.FileHandler(filename='sdct.log')
file_handler.setFormatter(Formatter('%(asctime)s [%(levelname)s]'
                                    '  %(name)s,%(lineno)s  %(message)s'))
file_handler.setLevel(DEBUG)

# console output
console_handler = logging.StreamHandler()
console_handler.setLevel(INFO)
console_handler.setFormatter(Formatter('%(message)s'))

sdct_logger = getLogger("sdct")
# add handlers
sdct_logger.addHandler(console_handler)
sdct_logger.addHandler(file_handler)
sdct_logger.setLevel(DEBUG)

logging.captureWarnings(True)


def get_logger(log_name, level=DEBUG):
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
    module_logger = sdct_logger.getChild(log_name)
    if level:
        module_logger.setLevel(level)
    return module_logger
