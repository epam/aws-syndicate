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

COMPENV_STATES = ('ENABLED', 'DISABLED')
COMPENV_TYPES = ('UNMANAGED', 'MANAGED')
COMPUTE_RESOURCE_TYPES = ('EC2', 'SPOT', 'FARGATE', 'FARGATE_SPOT')
FARGATE_RESOURCE_TYPES = ('FARGATE', 'FARGATE_SPOT')
ALLOCATION_STRATEGIES = ('BEST_FIT', 'BEST_FIT_PROGRESSIVE', 'SPOT_CAPACITY_OPTIMIZED')


def validate_batch_compenv(compenv_name, compenv_meta):
    new_meta = dict(
        resource_type=compenv_meta.get('resource_type'),
        compute_environment_type=compenv_meta.get('compute_environment_type'),
        state=compenv_meta.get('state'),
        service_role=compenv_meta.get('service_role')
    )

    state = compenv_meta.get('state')
    _validate_options_field('state', state, COMPENV_STATES, False)

    comenv_type = compenv_meta.get('compute_environment_type')
    _validate_options_field('compute_environment_type', comenv_type, COMPENV_TYPES, True)

    compute_resources = compenv_meta.get('compute_resources')
    if compute_resources:
        new_meta['compute_resources'] = _validate_compute_resources(compenv_meta)

    # return new_meta


def _validate_compute_resources(meta):
    compute_resources = meta['compute_resources']

    compute_resource_type = compute_resources.get('type')
    _validate_options_field('compute_resources__type', compute_resource_type, COMPUTE_RESOURCE_TYPES, required=True)

    allocation_strategy = compute_resources.get('allocation_strategy')
    _validate_options_field('compute_resources__allocation_strategy', allocation_strategy, ALLOCATION_STRATEGIES, False)
    if allocation_strategy and compute_resource_type in ('FARGATE', 'FARGATE_SPOT'):
        raise AssertionError(
            "compute_resources__allocation_strategy isn't applicable to jobs running on Fargate resources"
        )

    min_vcpus = compute_resources.get('minv_cpus')
    if min_vcpus:
        if compute_resource_type in ('FARGATE', 'FARGATE_SPOT'):
            raise AssertionError(
                "compute_resources__min_vcpus isn't applicable to jobs running on Fargate resources"
            )

        if not isinstance(min_vcpus, int):
            raise AssertionError(
                'compute_resources__min_vcpus must be an integer'
            )

    max_vcpus = compute_resources.get('maxv_cpus')
    if max_vcpus:
        if not isinstance(max_vcpus, int):
            raise AssertionError(
                'compute_resources__max_vcpus must be an integer'
            )
    else:
        raise AssertionError(
            "Missing required parameter: 'max_vpus'"
        )

    desired_vcpus = compute_resources.get('desiredv_cpus')
    if desired_vcpus:
        if not isinstance(desired_vcpus, int):
            raise AssertionError(
                'compute_resources__desired_vcpus must be an integer'
            )
        if desired_vcpus > max_vcpus:
            raise AssertionError(
                'compute_resources__desired_vcpus must be smaller or equal to max_vcpus'
            )
        if min_vcpus and desired_vcpus < min_vcpus:
            raise AssertionError(
                'compute_resources__desired_vcpus must be greater or equeal to min_vcpus'
            )

    instance_types = compute_resources.get('instance_types')
    if instance_types:
        if instance_types in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__instance_types parameter isn't applicable to "
                "jobs running on Fargate resources, and shouldn't be specified."
            )

    image_id = compute_resources.get('image_id')
    if image_id:
        if image_id in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__image_id parameter isn't applicable to jobs "
                "running on Fargate resources, and shouldn't be specified."
            )

    subnets = compute_resources.get('subnets')
    if not subnets:
        raise AssertionError(
            "Missing required parameter: 'subnets'"
        )

    security_group_ids = compute_resources.get('security_group_ids')
    if not security_group_ids and compute_resource_type in FARGATE_RESOURCE_TYPES:
        raise AssertionError(
            "compute_resources__security_group_ids is required for jobs running on Fargate resources"
        )

    ec2_keypair = compute_resources.get('ec2_key_pair')

    tags = compute_resources.get('tags')
    if tags:
        if compute_resource_type in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__tags parameter isn't applicable to jobs running on Fargate "
                "resources, and shouldn't be specified."
            )

    placement_group = compute_resources.get('placement_group')
    if placement_group:
        if compute_resource_type in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__placement_group parameter isn't applicable to jobs running on "
                "Fargate resources, and shouldn't be specified."
            )

    bid_percentage = compute_resources.get('bid_percentage')
    if bid_percentage:
        if not isinstance(bid_percentage, int):
            raise AssertionError(
                "compute_resources__bid_percentage must be an integer"
            )

    spot_iam_fleet_role = compute_resources.get('spot_iam_fleet_role')
    if spot_iam_fleet_role:
        if compute_resource_type in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__spot_iam_fleet_role parameter isn't applicable to jobs running on Fargate "
                "resources, and shouldn't be specified."
            )

    launch_template = compute_resources.get('launch_template')
    if launch_template:
        if compute_resource_type in FARGATE_RESOURCE_TYPES:
            raise AssertionError(
                "compute_resources__launch_tamplate parameter isn't applicable to jobs running on Fargate "
                "resources, and shouldn't be specified."
            )


def _validate_options_field(field_name, field_value, field_options, required=True):
    if not required and not field_value:
        return

    if required and not field_value:
        raise AssertionError(
            "Missing required Compute Environment field: '{0}'".format(field_name)
        )

    if field_value not in field_options:
        raise AssertionError(
            "Compute Environment field: '{0}':'{1}' must be one of the following: {2}"
                .format(field_name, str(field_value), field_options)
        )
