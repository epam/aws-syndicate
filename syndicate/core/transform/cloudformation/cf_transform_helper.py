"""
    Copyright 2021 EPAM Systems, Inc.

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
import re


def is_arn(line):
    return isinstance(line, str) and line.startswith('arn:')


def to_logic_name(resource_name):
    name_components = re.split('[^a-zA-Z0-9]', resource_name)
    formatted = []
    for component in name_components:
        component_len = len(component)
        if component_len > 1:
            formatted.append(component[0].upper() + component[1:])
        elif component_len == 1:
            formatted.append(component[0].upper())
    return ''.join(formatted)


def iam_role_logic_name(role_name):
    return to_logic_name(role_name)


def lambda_function_logic_name(function_name):
    return to_logic_name(function_name)


def lambda_alias_logic_name(function_name, alias):
    return to_logic_name('{}{}Alias'.format(
        function_name, alias.capitalize()))


def lambda_publish_version_logic_name(function_name):
    return to_logic_name('{}PublishVersion'.format(function_name))


def dynamodb_table_logic_name(table_name):
    return to_logic_name('{}Table'.format(table_name))
