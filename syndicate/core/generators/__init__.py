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

from syndicate.commons.log_helper import get_logger

_LOG = get_logger('syndicate.core.generators')


def _touch(path):
    try:
        with open(path, 'a'):
            os.utime(path, None)
    except OSError:
        raise RuntimeError('Can not create new file by path {}. Syndicate '
                           'does not have enough rights!'.format(path))


def _mkdir(path, exist_ok=False, fault_message=None):
    try:
        os.makedirs(path, exist_ok=exist_ok)
    except FileExistsError as e:
        if fault_message:
            answer = input(fault_message)
            re_survey(answer, path)
        else:
            _LOG.error(e)
    except OSError:
        raise RuntimeError('Can not create new folder by path {}. Syndicate '
                           'does not have enough rights!'.format(path))


def re_survey(answer, project_path):
    while answer not in ('y', 'n'):
        answer = input('Please enter [y/n] value: ')
        if answer == 'y':
            os.makedirs(project_path, exist_ok=True)
        elif answer == 'n':
            return


PYTHON_LAMBDA_HANDLER_TEMPLATE = """import json

def lambda_handler(event, context):
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
"""

NODEJS_LAMBDA_HANDLER_TEMPLATE = """exports.handler = async (event) => {
    // TODO implement
    const response = {
        statusCode: 200,
        body: JSON.stringify('Hello from Lambda!'),
    };
    return response;
};
"""
