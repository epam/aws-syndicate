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
from syndicate.commons.log_helper import get_logger
from syndicate.core.build.validator.batch_compenv_validator import validate_batch_compenv
from syndicate.core.build.validator.dynamodb_validator import \
    validate_dynamodb, validate_dax_cluster
from syndicate.core.build.validator.batch_jobdef_validator import validate_batch_jobdef
from syndicate.core.build.validator.lambda_validator import validate_lambda
from syndicate.core.constants import \
    (LAMBDA_CONFIG_FILE_NAME, LAMBDA_TYPE, DYNAMO_TABLE_TYPE,
     BATCH_COMPENV_TYPE, BATCH_JOBDEF_TYPE, DAX_CLUSTER_TYPE)

ALL_TYPES = 'all_types'

_LOG = get_logger('validator')


def common_validate(resource_meta, all_meta):
    dependencies = resource_meta.get('dependencies')
    if dependencies:
        for dependency in resource_meta['dependencies']:
            dependency_name = dependency.get('resource_name')
            if dependency_name not in list(all_meta.keys()):
                err_mess = ("One of resource dependencies wasn't "
                            "described: {0}. Please, describe this "
                            "resource in {1} if it is Lambda or in "
                            "deployment_resources.json"
                            .format(dependency_name,
                                    LAMBDA_CONFIG_FILE_NAME))
                raise AssertionError(err_mess)


# validation customization
VALIDATOR_BY_TYPE_MAPPING = {
    ALL_TYPES: common_validate,
    DYNAMO_TABLE_TYPE: validate_dynamodb,
    DAX_CLUSTER_TYPE: validate_dax_cluster,
    BATCH_COMPENV_TYPE: validate_batch_compenv,
    BATCH_JOBDEF_TYPE: validate_batch_jobdef,
    LAMBDA_TYPE: validate_lambda
}
