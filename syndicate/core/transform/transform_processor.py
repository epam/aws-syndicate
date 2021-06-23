#  Copyright 2021 EPAM Systems, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import json

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import resolve_bundle_directory
from syndicate.core.constants import BUILD_META_FILE_NAME
from syndicate.core.helper import build_path

_LOG = get_logger('syndicate.core.build.transform_processor')

TERRAFORM_DSL = 'terraform'
CLOUD_FORMATION_DSL = 'cloudformation'


def generate_build_meta(bundle_name, dsl_list, output_directory):
    bundle_path = resolve_bundle_directory(bundle_name=bundle_name)
    build_meta_path = build_path(bundle_path, BUILD_META_FILE_NAME)
    with open(build_meta_path) as build_meta_file:
        meta_resources = json.load(build_meta_file)

    for dsl in dsl_list:
        transformer = TRANSFORM_PROCESSORS.get(dsl)
        if not transformer:
            _LOG.warning(f'There is no transformer for such dsl: {dsl}')
            continue

        transformer(build_meta=meta_resources,
                    output_directory=output_directory)

    return None


def _generate_terraform_meta(build_meta, output_directory):
    return None


def _generate_cloud_formation_meta(build_meta, output_directory):
    return None


TRANSFORM_PROCESSORS = {
    TERRAFORM_DSL: _generate_terraform_meta,
    CLOUD_FORMATION_DSL: _generate_cloud_formation_meta
}
