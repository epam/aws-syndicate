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

from syndicate.exceptions import InvalidValueError
from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import resolve_bundle_directory
from syndicate.core.build.runtime.dotnet import assemble_dotnet_lambdas
from syndicate.core.build.runtime.java import assemble_java_mvn_lambdas
from syndicate.core.build.runtime.nodejs import assemble_node_lambdas
from syndicate.core.build.runtime.python import assemble_python_lambdas
from syndicate.core.build.runtime.swagger_ui import assemble_swagger_ui
from syndicate.core.build.runtime.appsync import assemble_appsync
from syndicate.core.groups import RUNTIME_SWAGGER_UI, RUNTIME_APPSYNC, \
    RUNTIME_JAVA, RUNTIME_NODEJS, RUNTIME_PYTHON, RUNTIME_DOTNET


SUPPORTED_RUNTIMES = [
    RUNTIME_JAVA,
    RUNTIME_NODEJS,
    RUNTIME_PYTHON,
    RUNTIME_DOTNET,
    RUNTIME_SWAGGER_UI,
    RUNTIME_APPSYNC
]

RUNTIME_TO_BUILDER_MAPPING = {
    RUNTIME_JAVA: assemble_java_mvn_lambdas,
    RUNTIME_NODEJS: assemble_node_lambdas,
    RUNTIME_PYTHON: assemble_python_lambdas,
    RUNTIME_DOTNET: assemble_dotnet_lambdas,
    RUNTIME_SWAGGER_UI: assemble_swagger_ui,
    RUNTIME_APPSYNC: assemble_appsync
}

_LOG = get_logger(__name__)


def assemble_artifacts(
    bundle_name: str, 
    runtime_root_dir: str,
    runtime: str,
    errors_allowed: bool = False,
    skip_tests: bool = False,
    **kwargs
) -> None:
    if runtime not in SUPPORTED_RUNTIMES:
        raise InvalidValueError(
            f"Runtime '{runtime}' is not supported. "
            f"Currently available runtimes:'{SUPPORTED_RUNTIMES}'")

    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)

    os.makedirs(bundle_dir, exist_ok=True)

    _LOG.debug(f'Target directory: {bundle_dir}')

    assemble_func = RUNTIME_TO_BUILDER_MAPPING.get(runtime)
    if not assemble_func:
        raise InvalidValueError(
            f"Runtime '{runtime}' is not supported. "
            f"Currently available runtimes:'{SUPPORTED_RUNTIMES}'")

    assemble_func(
        runtime_root_dir=runtime_root_dir,
        bundles_dir=bundle_dir,
        errors_allowed=errors_allowed,
        skip_tests=skip_tests
    )
