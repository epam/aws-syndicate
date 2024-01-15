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
from syndicate.core.build.validator.batch_compenv_validator import _validate_field_type

JOB_DEFINITION_TYPES = ('container', 'multinode')


def validate_batch_jobdef(jobdef_name, jobdef_meta):
    """
    Performs check of Batch Job Definition resources.
    :param jobdef_name: name of resource
    :param jobdef_meta: resource definition

    :raises AssertionError in case of invalidity.

    :return: None
    """
    jobdef_config = [
        {
            'field_name': 'job_definition_name',
            'field_value': jobdef_name,
            'prefix': '',
            'validators': [
                _validate_required_field
            ]
        },
        {
            'field_name': 'job_definition_type',
            'field_value': jobdef_meta.get('job_definition_type'),
            'field_options': JOB_DEFINITION_TYPES,
            'prefix': '',
            'required': True,
            'validators': [
                _validate_options_field
            ]
        },
        {
            'field_name': 'parameters',
            'field_value': jobdef_meta.get('parameters'),
            'prefix': '',
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'retry_strategy',
            'field_value': jobdef_meta.get('retry_strategy'),
            'prefix': '',
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'propagate_tags',
            'field_value': jobdef_meta.get('propagate_tags'),
            'prefix': '',
            'required_type': bool,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'timeout',
            'field_value': jobdef_meta.get('timeout'),
            'prefix': '',
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'tags',
            'field_value': jobdef_meta.get('tags'),
            'prefix': '',
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'platform_capabilities',
            'field_value': jobdef_meta.get('platform_capabilities'),
            'prefix': '',
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        }
    ]

    job_definition_type = jobdef_meta.get('job_definition_type')
    container_properties = jobdef_meta.get('container_properties')
    node_properties = jobdef_meta.get('node_properties')

    _process_config(jobdef_config)

    if job_definition_type == 'container':
        if not container_properties and not node_properties:
            raise AssertionError(
                "Either 'container_properties' or 'node_properties' must be specified "
                "for 'container' job definition type."
            )
    if container_properties:
        _validate_container_properties(container_properties)
    if node_properties:
        _validate_node_properties(node_properties)


def _validate_container_properties(container_properties, prefix=None):
    """
    Performs check of Batch Job Definition container properties.

    :param container_properties: container properties definition
    :param prefix: prefix that will be displayed before the variable
     name in case of invalidity.

    :raises AssertionError in case of invalidity.

    :return: None
    """
    if not prefix:
        prefix = 'container_properties'

    container_config = [
        {
            'field_name': 'image',
            'field_value': container_properties.get('image'),
            'prefix': prefix,
            'required_type': str,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'vcpus',
            'field_value': container_properties.get('vcpus'),
            'prefix': prefix,
            'required_type': int,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'memory',
            'field_value': container_properties.get('memory'),
            'prefix': prefix,
            'required_type': int,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'command',
            'field_value': container_properties.get('command'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'job_role_arn',
            'field_value': container_properties.get('job_role_arn'),
            'prefix': prefix,
            'required_type': str,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'execution_role_arn',
            'field_value': container_properties.get('execution_role_arn'),
            'prefix': prefix,
            'required_type': str,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'volumes',
            'field_value': container_properties.get('volumes'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'volumes',
            'field_value': container_properties.get('volumes'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'environment',
            'field_value': container_properties.get('environment'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'mount_points',
            'field_value': container_properties.get('mount_points'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'readonly_root_filesystem',
            'field_value': container_properties.get('readonly_root_filesystem'),
            'prefix': prefix,
            'required_type': bool,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'privileged',
            'field_value': container_properties.get('privileged'),
            'prefix': prefix,
            'required_type': bool,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'ulimits',
            'field_value': container_properties.get('ulimits'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'user',
            'field_value': container_properties.get('user'),
            'prefix': prefix,
            'required_type': str,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'instance_type',
            'field_value': container_properties.get('instance_type'),
            'prefix': prefix,
            'required_type': str,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'resource_requirements',
            'field_value': container_properties.get('resource_requirements'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'linux_parameters',
            'field_value': container_properties.get('linux_parameters'),
            'prefix': prefix,
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'log_configuration',
            'field_value': container_properties.get('log_configuration'),
            'prefix': prefix,
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'secrets',
            'field_value': container_properties.get('secrets'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'network_configuration',
            'field_value': container_properties.get('network_configuration'),
            'prefix': prefix,
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
        {
            'field_name': 'fargate_platform_configuration',
            'field_value': container_properties.get('fargate_platform_configuration'),
            'prefix': prefix,
            'required_type': dict,
            'validators': [
                _validate_field_type
            ]
        },
    ]
    _process_config(container_config)


def _validate_node_properties(node_properties):
    """
    Performs check of Batch Job Definition node properties.
    :param node_properties: container properties definition

    :raises AssertionError in case of invalidity.

    :return: None
    """
    prefix = "node_properties"

    node_config = [
        {
            'field_name': 'num_nodes',
            'field_value': node_properties.get('num_nodes'),
            'prefix': prefix,
            'required_type': int,
            'validators': [
                _validate_field_type,
                _validate_required_field
            ]
        },
        {
            'field_name': 'main_node',
            'field_value': node_properties.get('main_node'),
            'prefix': prefix,
            'required_type': int,
            'validators': [
                _validate_field_type,
                _validate_required_field
            ]
        },
        {
            'field_name': 'node_range_properties',
            'field_value': node_properties.get('node_range_properties'),
            'prefix': prefix,
            'required_type': list,
            'validators': [
                _validate_field_type,
                _validate_required_field
            ]
        },
    ]
    _process_config(node_config)

    node_range_properties = node_properties.get('node_range_properties')

    node_range_prefix = prefix + "__node_range_properties"
    for node in node_range_properties:
        container_properties = node.get('container')
        _validate_required_field(
            field_name='container',
            field_value=container_properties,
            prefix=node_range_prefix
        )
        _validate_field_type(
            field_name='container',
            field_value=node.get('container'),
            prefix=node_range_prefix,
            required_type=dict,
        )

        container_prefix = node_range_prefix + '__container'
        _validate_container_properties(container_properties, prefix=container_prefix)


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
            "Missing required Job Definition field: '{0}'".format(field_name)
        )
    if field_value not in field_options:
        raise AssertionError(
            "Job Definition field: '{0}':'{1}' must be one of the following: {2}"
                .format(field_name, str(field_value), field_options)
        )


def _validate_required_field(field_name, field_value, prefix='', **kwargs):
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
            "Missing required Job Definition field: {0}".format(field_name)
        )


def _process_config(config):
    for parameter in config:
        for validator in parameter.get('validators'):
            validator(**parameter)
