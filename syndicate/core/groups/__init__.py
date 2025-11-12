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
RUNTIME_JAVA = 'java'
RUNTIME_NODEJS = 'nodejs'
RUNTIME_PYTHON = 'python'
RUNTIME_DOTNET = 'dotnet'
RUNTIME_SWAGGER_UI = 'swagger_ui'
RUNTIME_APPSYNC = 'appsync'
RUNTIME = 'runtime'
LAYER_SUFFIX = '_layer'
RUNTIME_PYTHON_LAYER = f'{RUNTIME_PYTHON}{LAYER_SUFFIX}'
RUNTIME_NODEJS_LAYER = f'{RUNTIME_NODEJS}{LAYER_SUFFIX}'
RUNTIME_DOTNET_LAYER = f'{RUNTIME_DOTNET}{LAYER_SUFFIX}'

JAVA_ROOT_DIR_JSRC = 'jsrc/main/java'
JAVA_ROOT_DIR_JAPP = 'japp'
NODEJS_ROOT_DIR = 'app'
PYTHON_ROOT_DIR_SRC = 'src'
PYTHON_ROOT_DIR_PYAPP = 'pyapp'
DOTNET_ROOT_DIR = 'dnapp'
SWAGGER_UI_ROOT_DIR = 'swagger_src'
APPSYNC_ROOT_DIR = 'appsync_src'

DEFAULT_RUNTIME_VERSION = {
    RUNTIME_PYTHON: 'python3.10',
    RUNTIME_NODEJS: 'nodejs20.x',
    RUNTIME_DOTNET: 'dotnet8'
}

TESTS_DIR_LOCATIONS = {
    PYTHON_ROOT_DIR_SRC: '',
    PYTHON_ROOT_DIR_PYAPP: PYTHON_ROOT_DIR_PYAPP,
}
