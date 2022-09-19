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
import json
import os

import click

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.helper import resolve_bundle_directory
from syndicate.core.constants import BUILD_META_FILE_NAME
from syndicate.core.helper import build_path
from syndicate.core.transform.cloudformation.cloudformation_transformer import \
    CloudFormationTransformer
from syndicate.core.transform.terraform.terraform_transformer import TerraformTransformer

_LOG = get_logger('syndicate.core.build.transform_processor')

TERRAFORM_DSL = 'terraform'
CLOUD_FORMATION_DSL = 'cloudformation'

TRANSFORM_PROCESSORS = {
    TERRAFORM_DSL: TerraformTransformer,
    CLOUD_FORMATION_DSL: CloudFormationTransformer
}


def generate_build_meta(bundle_name, dsl_list, output_directory):
    bundle_path = resolve_bundle_directory(bundle_name=bundle_name)
    build_meta_path = build_path(bundle_path, BUILD_META_FILE_NAME)
    with open(build_meta_path) as build_meta_file:
        meta_resources = json.load(build_meta_file)

    for dsl in dsl_list:

        transformer_type = TRANSFORM_PROCESSORS.get(dsl)
        if not transformer_type:
            click.echo(f'There is no transformer for the dsl: {dsl}')
            continue

        transformer = transformer_type(bundle_name=bundle_name)
        transformed_build_meta = \
            transformer.transform_build_meta(build_meta=meta_resources)
        if not output_directory:
            output_path = build_path(
                bundle_path, transformer.output_file_name())
        elif not os.path.isabs(output_directory):
            output_path = build_path(
                os.getcwd(), output_directory, transformer.output_file_name())
        else:
            output_path = build_path(
                output_directory, transformer.output_file_name())
        with open(output_path, 'w') as output_file:
            output_file.write(transformed_build_meta)
        click.echo(f"The '{bundle_name}' bundle is transformed into {dsl} dsl.")
