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
from syndicate.core.build.helper import resolve_bundle_directory
from syndicate.core.build.runtime.java import assemble_java_mvn_lambdas
from syndicate.core.build.runtime.nodejs import assemble_node_lambdas
from syndicate.core.build.runtime.python import assemble_python_lambdas

RUNTIME_JAVA_8 = 'java8'
RUNTIME_NODEJS = 'nodejs10.x'
RUNTIME_PYTHON = 'pythonX'

SUPPORTED_RUNTIMES = [
    RUNTIME_JAVA_8,
    RUNTIME_NODEJS,
    RUNTIME_PYTHON
]

RUNTIME_TO_BUILDER_MAPPING = {
    RUNTIME_JAVA_8: assemble_java_mvn_lambdas,
    RUNTIME_NODEJS: assemble_node_lambdas,
    RUNTIME_PYTHON: assemble_python_lambdas
}

_LOG = get_logger('syndicate.core.build.artifact_processor')


def assemble_artifacts(bundle_name, project_path, runtime):
    if runtime not in SUPPORTED_RUNTIMES:
        raise AssertionError(
            'Runtime {} is not supported. '
            'Currently available runtimes:{}'.format(runtime,
                                                     SUPPORTED_RUNTIMES))

    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)
    if not os.path.exists(bundle_dir):
        os.makedirs(bundle_dir)
    _LOG.debug('Target directory: {0}'.format(bundle_dir))

    assemble_func = RUNTIME_TO_BUILDER_MAPPING.get(runtime)
    if not assemble_func:
        raise AssertionError(
            'There is no assembler for the runtime {}'.format(runtime))
    assemble_func(project_path=project_path,
                  bundles_dir=bundle_dir)
