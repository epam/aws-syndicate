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
import shutil

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import resolve_bundle_directory
from syndicate.core.build.runtime.dotnet import assemble_dotnet_lambdas
from syndicate.core.build.runtime.java import assemble_java_mvn_lambdas
from syndicate.core.build.runtime.nodejs import assemble_node_lambdas
from syndicate.core.build.runtime.python import assemble_python_lambdas
from syndicate.core.build.runtime.swagger_ui import assemble_swagger_ui

RUNTIME_JAVA = 'javaX'
RUNTIME_NODEJS = 'nodejs20.x'
RUNTIME_PYTHON = 'pythonX'
RUNTIME_DOTNET = 'dotnet8'
RUNTIME_SWAGGER_UI = 'swagger_ui'

SUPPORTED_RUNTIMES = [
    RUNTIME_JAVA,
    RUNTIME_NODEJS,
    RUNTIME_PYTHON,
    RUNTIME_DOTNET,
    RUNTIME_SWAGGER_UI
]

RUNTIME_TO_BUILDER_MAPPING = {
    RUNTIME_JAVA: assemble_java_mvn_lambdas,
    RUNTIME_NODEJS: assemble_node_lambdas,
    RUNTIME_PYTHON: assemble_python_lambdas,
    RUNTIME_DOTNET: assemble_dotnet_lambdas,
    RUNTIME_SWAGGER_UI: assemble_swagger_ui
}

_LOG = get_logger('syndicate.core.build.artifact_processor')


def assemble_artifacts(bundle_name, project_path, runtime, force_upload=None):
    if runtime not in SUPPORTED_RUNTIMES:
        raise AssertionError(
            'Runtime {} is not supported. '
            'Currently available runtimes:{}'.format(runtime,
                                                     SUPPORTED_RUNTIMES))

    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)

    if force_upload is True:
        _LOG.warning(f"Force upload is True, going to check if bundle"
                     f" directory already exists.")
        normalized_bundle_dir = os.path.normpath(bundle_dir)
        if os.path.exists(normalized_bundle_dir):
            _LOG.warning(f"Bundle with name: {bundle_name} already exists by"
                         f" path `{normalized_bundle_dir}`, going to remove"
                         f" this bundle locally.")
            shutil.rmtree(normalized_bundle_dir)

    os.makedirs(bundle_dir, exist_ok=True)
    _LOG.debug('Target directory: {0}'.format(bundle_dir))

    assemble_func = RUNTIME_TO_BUILDER_MAPPING.get(runtime)
    if not assemble_func:
        raise AssertionError(
            'There is no assembler for the runtime {}'.format(runtime))
    assemble_func(project_path=project_path,
                  bundles_dir=bundle_dir)
