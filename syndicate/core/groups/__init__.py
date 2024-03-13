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
RUNTIME_SWAGGER_UI = 'swagger_ui'
RUNTIME = 'runtime'
RUNTIME_PYTHON_LAYER = 'python_layer'
RUNTIME_NODEJS_LAYER = 'nodejs_layer'

DEFAULT_RUNTIME_VERSION = {
        RUNTIME_PYTHON: 'python3.10',
        RUNTIME_NODEJS: 'nodejs20.x'
    }
