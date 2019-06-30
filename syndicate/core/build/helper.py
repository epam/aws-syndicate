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
import re

from syndicate.core.constants import LAMBDA_SOURCE_FILE_ENDING


def build_py_package_name(lambda_name, lambda_version):
    return '{0}-{1}.zip'.format(lambda_name, lambda_version)


_LAMBDA_META_REGX = '>{2}\\s*.*'
_LAMBDA_HANDLER_FUNC_REGEX = 'def\\s+.+\\(event, context\\):'

LAMBDA_META_WITH_DEFAULT_VALUES = {
    'name': None,
    'iam_role_name': None,
    'func_name': None,
    'lambda_path': None,
    'version': '1.0',
    'runtime': 'python3.7',
    'memory': 128,
    'timeout': 900,
    'resource_type': 'lambda',
    'dependencies': [],
    'event_sources': [],
    'env_variables': {},
    'publish_version': False
}
# func_name
# runtime=python3.7
# memory=128
# timeout=900
# lambda_path=/lambdas/sdct-add-customer

default_meta = {
    "version": "1.0",
    "resource_type": "lambda",
    "dependencies": [],
    "event_sources": [],
    "env_variables": {}
}


def get_lambda_properties_from_python_code(file_name, path, project_path):
    with open('{0}/{1}'.format(path, file_name), 'r') as file:
        file_content = file.read()
        properties = re.findall(_LAMBDA_META_REGX, file_content)

        if not properties:
            return
        properties = [item.replace('>>', '').strip() for item in properties]
        props_from_source_file = _convert_properties_to_dict(properties)

        lambda_meta = default_meta.copy()
        lambda_definition = {**lambda_meta, **props_from_source_file}

        # get lambda path
        lambda_path = path.replace(project_path, '')
        lambda_definition['lambda_path'] = '/' + lambda_path

        # get lambda handler
        lambda_definition['func_name'] = generate_func_name(
            file_name=file_name,
            file_content=file_content)

        lambda_definition = fill_with_defaults(lambda_definition)
        check_for_integrity(lambda_definition)

    return lambda_definition


def generate_func_name(file_name, file_content):
    lambda_handler_functions = re.findall(_LAMBDA_HANDLER_FUNC_REGEX,
                                          file_content)
    if len(lambda_handler_functions) > 1:
        raise AssertionError(
            'There are several functions that supposed to be '
            'lambda handlers: {0}. Please specify one for '
            'lambda in file: {1}'.format(lambda_handler_functions, file_name))
    # parsing string
    function = lambda_handler_functions[0]
    function = function.replace('def', '').strip()
    function = function.split('(')[0]

    lambda_handler_file = file_name.replace(LAMBDA_SOURCE_FILE_ENDING, '')
    lambda_handler = '{0}.{1}'.format(lambda_handler_file,
                                      function)
    return lambda_handler


def _convert_properties_to_dict(properties):
    props_dict = {}
    for item in properties:
        item = _remove_brackets(item)
        split = item.split('=')
        if not len(split) == 2:
            raise AssertionError(
                'Malformed property: {0}. Format: key=value'.format(item))
        prop_key = split[0]
        prop_value = split[1]
        if prop_key == 'env_variables':
            pairs = prop_value.split(',')
            variables = {}
            for pair in pairs:
                pair_items = pair.split(':')
                variables[pair_items[0].strip()] = pair_items[1].strip()
            props_dict[prop_key] = variables
        elif prop_key == 'dependencies':
            pairs = prop_value.split(',')
            dependencies = []
            for pair in pairs:
                pair_items = pair.split(':')
                dependencies.append({
                    'resource_type': pair_items[0].strip(),
                    'resource_name': pair_items[1].strip()
                })
            props_dict[prop_key] = dependencies
        else:
            prop_value = cast_to_type(prop_value)
            props_dict[prop_key] = prop_value
    return props_dict


def _process_meta_value(value):
    if '[' in value:  # it is a list
        value = _remove_brackets(value)
        values = value.split(',')
        value = values
    return value


def _remove_brackets(value):
    value = value.replace('[', '')
    value = value.replace(']', '')
    return value


def fill_with_defaults(lambda_def):
    for key, value in LAMBDA_META_WITH_DEFAULT_VALUES.items():
        lambda_property = lambda_def.get(key)
        if not lambda_property:
            if value is not None:
                lambda_def[key] = value
    return lambda_def


def check_for_integrity(lambda_def):
    missing_keys = []
    for key, value in LAMBDA_META_WITH_DEFAULT_VALUES.items():
        lambda_property = lambda_def.get(key)
        if lambda_property is None:
            missing_keys.append(key)

    if missing_keys:
        raise AssertionError(
            'Lambda definition is not complete. Missing keys: {0}'.format(
                missing_keys))
    return lambda_def


def cast_to_type(value):
    try:
        value = int(value)
    except ValueError:
        pass  # no handling required

    if value == 'true':
        value = True
    elif value == 'false':
        value = False

    return value
