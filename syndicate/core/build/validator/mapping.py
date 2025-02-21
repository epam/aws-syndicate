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
from syndicate.exceptions import ResourceMetadataError
from syndicate.commons.log_helper import get_logger
from syndicate.core.build.validator.batch_compenv_validator import validate_batch_compenv
from syndicate.core.build.validator.dynamodb_validator import \
    validate_dynamodb, validate_dax_cluster
from syndicate.core.build.validator.batch_jobdef_validator import validate_batch_jobdef
from syndicate.core.build.validator.lambda_validator import validate_lambda
from syndicate.core.build.validator.ec2_launch_template_validator import \
    validate_launch_template
from syndicate.core.constants import \
    (LAMBDA_TYPE, DYNAMO_TABLE_TYPE,
     BATCH_COMPENV_TYPE, BATCH_JOBDEF_TYPE, DAX_CLUSTER_TYPE,
     EC2_LAUNCH_TEMPLATE_TYPE, RESOURCE_LIST)

ALL_TYPES = 'all_types'

_LOG = get_logger(__name__)


def common_validate(resource_name, resource_meta, all_meta):
    dependencies = resource_meta.get('dependencies')
    if dependencies:
        for dependency in dependencies:
            errors = []

            if not dependency.get('resource_name'):
                errors.append(
                    f"There is no 'resource_name' in resource "
                    f"'{resource_name}' dependency {dependency}")
            elif dependency.get('resource_name') not in list(all_meta.keys()):
                errors.append(
                    f"The resource '{resource_name}' depends on resource "
                    f"'{dependency.get('resource_name')}' that is not a part "
                    f"of the project. Please double-check the project "
                    f"resources description add it to the project or remove "
                    f"it from the resource '{resource_name}' dependencies.")

            if not dependency.get('resource_type'):
                errors.append(
                    f"There is no 'resource_type' in resource "
                    f"'{resource_name}' dependency {dependency}")
            elif dependency.get('resource_type') not in RESOURCE_LIST:
                errors.append(
                    f"Unsupported resource type "
                    f"'{dependency.get('resource_type')}' found in "
                    f"the resource '{resource_name}' dependency "
                    f"'{dependency}'.")
            if errors:
                raise ResourceMetadataError(str(errors))


# validation customization
VALIDATOR_BY_TYPE_MAPPING = {
    ALL_TYPES: common_validate,
    DYNAMO_TABLE_TYPE: validate_dynamodb,
    DAX_CLUSTER_TYPE: validate_dax_cluster,
    BATCH_COMPENV_TYPE: validate_batch_compenv,
    BATCH_JOBDEF_TYPE: validate_batch_jobdef,
    LAMBDA_TYPE: validate_lambda,
    EC2_LAUNCH_TEMPLATE_TYPE: validate_launch_template
}
