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
from syndicate.connection.ec2_connection import InstanceTypes
from syndicate.core.constants import OPTIMAL_INSTANCE_TYPE

COMPENV_STATES = ('ENABLED', 'DISABLED')
COMPENV_TYPES = ('UNMANAGED', 'MANAGED')
COMPUTE_RESOURCE_TYPES = ('EC2', 'SPOT', 'FARGATE', 'FARGATE_SPOT')
FARGATE_RESOURCE_TYPES = ('FARGATE', 'FARGATE_SPOT')
ALLOCATION_STRATEGIES = ('BEST_FIT', 'BEST_FIT_PROGRESSIVE', 'SPOT_CAPACITY_OPTIMIZED')


def validate_batch_compenv(compenv_name, compenv_meta):
    """
    Performs check of Batch Compute Environment resources.
    :param compenv_name: name of resource
    :param compenv_meta: resource definition

    :raises AssertionError in case of invalidity.

    :return: None
    """
    # Config stores a list of validation rules for each parameter.
    # Each rule contains:
    # - 'field name' - variable name that will be displayed in case of invalidity
    # - 'field value' - parameter value
    # - 'validators' - list of validator functions to test parameter
    # - any other arguments that will be passed to validator
    config = [
        {
            'field_name': 'compute_environment_name',
            'field_value': compenv_name,
            'prefix': '',
            'validators': [
                _validate_required_field
            ]
        },
        {
            'field_name': 'state',
            'field_value': compenv_meta.get('state'),
            'field_options': COMPENV_STATES,
            'prefix': '',
            'required': False,
            'validators': [
                _validate_options_field
            ]
        },
        {
            'field_name': 'compute_environment_type',
            'field_value': compenv_meta.get('compute_environment_type'),
            'field_options': COMPENV_TYPES,
            'prefix': '',
            'required': True,
            'validators': [
                _validate_options_field
            ]
        },
    ]
    _process_config(config)

    compute_resources = compenv_meta.get('compute_resources')
    if compute_resources:
        _validate_compute_resources(compute_resources)


def _validate_compute_resources(compute_resources):
    """
    Performs check of Batch Compute Environment compute resources.
    :param compute_resources: compute resources definition

    :raises AssertionError in case of invalidity.

    :return: None
    """
    compute_resource_type = compute_resources.get('type')
    compute_resource_config = [
        {
            'field_name': 'compute_resource_type',
            'field_value': compute_resource_type,
            'field_options': COMPUTE_RESOURCE_TYPES,
            'required': True,
            'validators': [
                _validate_options_field
            ]
        },
        {
            'field_name': 'allocation_strategy',
            'field_value': compute_resources.get('allocation_strategy'),
            'field_options': ALLOCATION_STRATEGIES,
            'compute_resource_type': compute_resource_type,
            'required': False,
            'validators': [
                _validate_options_field,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'min_vcpus',
            'field_value': compute_resources.get('minv_cpus'),
            'compute_resource_type': compute_resource_type,
            'required_type': int,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'maxv_cpus',
            'field_value': compute_resources.get('maxv_cpus'),
            'compute_resource_type': compute_resource_type,
            'required_type': int,
            'validators': [
                _validate_required_field,
                _validate_field_type,
            ]
        },
        {
            'field_name': 'desiredv_cpus',
            'field_value': compute_resources.get('desiredv_cpus'),
            'compute_resource_type': compute_resource_type,
            'required_type': int,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'instance_types',
            'field_value': compute_resources.get('instance_types'),
            'compute_resource_type': compute_resource_type,
            'required_type': list,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field,
            ]
        },
        {
            'field_name': 'image_id',
            'field_value': compute_resources.get('image_id'),
            'compute_resource_type': compute_resource_type,
            'required_type': str,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'subnets',
            'field_value': compute_resources.get('subnets'),
            'required_type': list,
            'validators': [
                _validate_required_field,
                _validate_field_type,
            ]
        },
        {
            'field_name': 'security_group_ids',
            'field_value': compute_resources.get('security_group_ids'),
            'required_type': list,
            'validators': [
                _validate_field_type,
            ]
        },
        {
            'field_name': 'ec2_key_pair',
            'field_value': compute_resources.get('ec2_key_pair'),
            'required_type': str,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'instance_role',
            'field_value': compute_resources.get('instance_role'),
            'required_type': str,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'tags',
            'field_value': compute_resources.get('tags'),
            'required_type': dict,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'placement_group',
            'field_value': compute_resources.get('placement_group'),
            'required_type': str,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'bid_percentage',
            'field_value': compute_resources.get('bid_percentage'),
            'required_type': int,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'spot_iam_fleet_role',
            'field_value': compute_resources.get('spot_iam_fleet_role'),
            'required_type': str,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'launch_template',
            'field_value': compute_resources.get('launch_template'),
            'required_type': dict,
            'compute_resource_type': compute_resource_type,
            'validators': [
                _validate_field_type,
                _validate_fargate_forbidden_field
            ]
        },
        {
            'field_name': 'ec2_configuration',
            'field_value': compute_resources.get('ec2_configuration'),
            'required_type': list,
            'validators': [
                _validate_field_type,
            ]
        },
    ]
    _process_config(compute_resource_config)

    instance_types = compute_resources.get('instance_types') or []
    # available = set(InstanceTypes.with_groups(
    #     InstanceTypes.from_api(region_name=CONFIG.region)
    # ))
    available = set(InstanceTypes.with_groups(InstanceTypes.from_botocore()))
    available.add(OPTIMAL_INSTANCE_TYPE)
    for instance_type in instance_types:
        _validate_options_field(
            field_name='instance_types__item',
            field_value=instance_type,
            field_options=available
        )

    desiredv_cpus = compute_resources.get('desiredv_cpus')
    if desiredv_cpus:
        minv_cpus = compute_resources.get('minv_cpus')
        maxv_cpus = compute_resources.get('maxv_cpus')
        if desiredv_cpus > maxv_cpus:
            raise AssertionError(
                'compute_resources__desired_vcpus must be smaller or equal than max_vcpus.'
            )
        if minv_cpus and desiredv_cpus < minv_cpus:
            raise AssertionError(
                'compute_resources__desired_vcpus must be greater or equal than min_vcpus.'
            )

    security_group_ids = compute_resources.get('security_group_ids')
    if not security_group_ids and compute_resource_type in FARGATE_RESOURCE_TYPES:
        raise AssertionError(
            "compute_resources__security_group_ids is required for jobs running on Fargate resources"
        )

    launch_template = compute_resources.get('launch_template')
    if launch_template:
        launch_template_id = launch_template.get('launch_template_id')
        _validate_field_type(
            field_name='launch_template_id',
            field_value=launch_template_id,
            prefix='compute_resources__launch_template',
            required_type=str
        )

        launch_template_name = launch_template.get('launch_template_name')
        _validate_field_type(
            field_name='launch_template_name',
            field_value=launch_template_name,
            prefix='compute_resources__launch_template',
            required_type=str
        )

        launch_template_options = (launch_template_id, launch_template_name)
        if all(launch_template_options) or not any(launch_template_options):
            raise AssertionError(
                "You must specify either the 'launch_template_id' or 'launch_template_name', but not both."
            )


def _validate_options_field(field_name, field_value, field_options, prefix='compute_resources', required=True,
                            **kwargs):
    """
    Checks whether a field contains value from options list.

    :param field_name: name of field that will be displayed in case of invalidity
    :param field_value: value of field to check
    :param field_options: list of options that field can accept
    :param prefix: prefix that will be displayed before field_name in case of invalidity
    :param required: if field is required and can be empty

    :raises AssertionError in case of invalidity.

    :return: None
    """
    if prefix:
        field_name = prefix + '__' + field_name

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


def _validate_fargate_forbidden_field(field_name, field_value, compute_resource_type, prefix='compute_resources',
                                      **kwargs):
    """
    Checks whether a field is forbidden to set for Fargate resources.

    :param field_name: name of field that will be displayed in case of invalidity
    :param field_value: value of field to check
    :param compute_resource_type: current compute resource type
    :param prefix: prefix that will be displayed before field_name in case of invalidity

    :raises AssertionError in case if compute resource type belongs to Fargate resources and given field is not empty.

    :return: None
    """
    if prefix:
        field_name = prefix + '__' + field_name
    if field_value and compute_resource_type in FARGATE_RESOURCE_TYPES:
        raise AssertionError(
            "{0} parameter isn't applicable to jobs running on Fargate resources, "
            "and shouldn't be specified.".format(field_name)
        )


def _validate_required_field(field_name, field_value, prefix='compute_resources', **kwargs):
    """
    Checks whether a field is not empty.

    :param field_name: name of field that will be displayed in case of invalidity
    :param field_value: value of field to check
    :param prefix: prefix that will be displayed before field_name in case of invalidity

    :raises AssertionError in case of invalidity.

    :return: None
    """
    if prefix:
        field_name = prefix + '__' + field_name

    if not field_value:
        raise AssertionError(
            "Missing required Compute Environment field: {0}".format(field_name)
        )


def _validate_field_type(field_name, field_value, required_type, prefix='compute_resources', **kwargs):
    """
    Checks whether a field is instance of the given type.

    :param field_name: name of field that will be displayed in case of invalidity
    :param field_value: value of field to check
    :param required_type: required type
    :param prefix: prefix that will be displayed before field_name in case of invalidity

    :raises AssertionError in case of invalidity.

    :return: None
    """
    if prefix:
        field_name = prefix + '__' + field_name

    if field_value is not None and not isinstance(field_value, required_type):
        raise AssertionError(
            "{0} parameter must be a {1}.".format(field_name, required_type.__name__)
        )


def _process_config(config):
    for parameter in config:
        for validator in parameter.get('validators'):
            validator(**parameter)
