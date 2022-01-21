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
from troposphere import awslambda

from syndicate.core.constants import S3_PATH_NAME
from syndicate.core.resources.helper import validate_params
from syndicate.core.resources.lambda_resource import \
    LAMBDA_LAYER_REQUIRED_PARAMS
from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import lambda_layer_logic_name


class CfLambdaLayerConverter(CfResourceConverter):

    def convert(self, name, meta):
        validate_params(name, meta, LAMBDA_LAYER_REQUIRED_PARAMS)

        logic_name = lambda_layer_logic_name(name)
        layer = awslambda.LayerVersion(logic_name)

        layer.Content = awslambda.Content(
            S3Bucket=self.config.deploy_target_bucket,
            S3Key=meta[S3_PATH_NAME])
        layer.LayerName = name
        layer.CompatibleRuntimes = meta['runtimes']

        if meta.get('description'):
            layer.Description = meta['description']
        if meta.get('license'):
            layer.LicenseInfo = meta['license']
        self.template.add_resource(layer)
