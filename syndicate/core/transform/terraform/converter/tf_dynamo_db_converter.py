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
from syndicate.core.resources.dynamo_db_resource import DynamoDBResource, \
    DYNAMODB_TABLE_REQUIRED_PARAMS, AUTOSCALING_REQUIRED_PARAMS
from syndicate.core.resources.helper import validate_params
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_role_arn_ref, build_aws_appautoscaling_target_resource_id_ref, \
    build_aws_appautoscaling_target_scalable_dimension_ref, \
    build_aws_appautoscaling_target_service_namespace_ref


class DynamoDbConverter(TerraformResourceConverter):

    def _add_index_keys_to_definition(self, attributes, index):
        self._append_attr_definition(attributes, index["index_key_name"],
                                     index["index_key_type"])
        if index.get('index_sort_key_name'):
            self._append_attr_definition(attributes,
                                         index["index_sort_key_name"],
                                         index["index_sort_key_type"])

    @staticmethod
    def _append_attr_definition(attributes, attr_name, attr_type):
        for each in attributes:
            if each['name'] == attr_name:
                return
        attributes.append(dict(name=attr_name,
                               type=attr_type))

    def convert(self, name, resource):
        validate_params(name, resource, DYNAMODB_TABLE_REQUIRED_PARAMS)

        hash_key_name = resource.get('hash_key_name')
        hash_key_type = resource.get('hash_key_type')
        sort_key_name = resource.get('sort_key_name')
        sort_key_type = resource.get('sort_key_type')
        read_capacity = resource.get('read_capacity', 1)
        write_capacity = resource.get('write_capacity', 1)
        stream_view_type = resource.get('stream_view_type')

        global_indexes = resource.get('global_indexes', [])
        local_indexes = resource.get('local_indexes', [])

        attributes = self._extract_attributes(global_indexes=global_indexes,
                                              local_indexes=local_indexes,
                                              hash_key_type=hash_key_type,
                                              hash_key=hash_key_name,
                                              sort_key_name=sort_key_name,
                                              sort_key_type=sort_key_type)

        dynamo_db_template = generate_tf_template_for_dynamo_table(
            hash_key=hash_key_name,
            range_key=sort_key_name,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_name=name,
            stream_view_type=stream_view_type,
            attributes=attributes,
            global_indexes=global_indexes,
            local_indexes=local_indexes)
        self.template.add_aws_dynamodb_table(meta=dynamo_db_template)

        autoscaling = resource.get('autoscaling', [])
        for aut in autoscaling:
            validate_params(name, aut, AUTOSCALING_REQUIRED_PARAMS)

            max_capacity = str(aut.get('max_capacity'))
            min_capacity = str(aut.get('min_capacity'))
            dimension = aut.get('dimension')
            resource_name = aut.get('resource_name')
            role_name = aut.get('role_name')

            tf_target_resource_name = build_terraform_resource_name(name,
                                                                    'scalable_target')
            resource_id = DynamoDBResource.build_res_id(dimension=dimension,
                                                        resource_name=resource_name,
                                                        table_name=name)
            target = dynamodb_scalable_target(resource_id=resource_id,
                                              scalable_dimension=dimension,
                                              min_capacity=min_capacity,
                                              max_capacity=max_capacity,
                                              role_name=role_name,
                                              tf_target_resource_name=tf_target_resource_name)

            autoscaling_policy = aut.get('config')
            if autoscaling_policy:
                target_utilization = autoscaling_policy['target_utilization']
                scale_in_cooldown = autoscaling_policy.get('scale_in_cooldown')
                scale_out_cooldown = autoscaling_policy.get(
                    'scale_out_cooldown')
                metric_type = 'DynamoDBWriteCapacityUtilization' \
                    if 'Write' in dimension \
                    else 'DynamoDBReadCapacityUtilization'
                tf_resource_name = build_terraform_resource_name(
                    'dynamodb-test-table_read_policy', resource_name)
                target_policy = dynamo_db_autoscaling_target_policy(
                    target_name=tf_target_resource_name,
                    target_value=target_utilization,
                    predefined_metric_type=metric_type,
                    scale_in_cooldown=scale_in_cooldown,
                    scale_out_cooldown=scale_out_cooldown,
                    tf_resource_name=tf_resource_name)
                self.template.add_aws_appautoscaling_target(meta=target)
                self.template.add_aws_appautoscaling_policy(meta=target_policy)

    def _extract_attributes(self, hash_key,
                            hash_key_type, sort_key_name=None,
                            sort_key_type=None,
                            global_indexes=None, local_indexes=None):
        attributes = [{'name': hash_key,
                       'type': hash_key_type}]

        if sort_key_name:
            attributes.append({'name': sort_key_name, 'type': sort_key_type})

        if global_indexes:
            for index in global_indexes:
                self._add_index_keys_to_definition(attributes=attributes,
                                                   index=index)
        if local_indexes:
            for index in local_indexes:
                self._add_index_keys_to_definition(attributes=attributes,
                                                   index=index)
        return attributes


def generate_tf_template_for_dynamo_table(table_name, hash_key,
                                          range_key,
                                          read_capacity,
                                          write_capacity,
                                          attributes,
                                          stream_view_type=None,
                                          global_indexes=None,
                                          local_indexes=None):
    gl_index_definitions = []
    for gind in global_indexes:
        index = {
            'name': gind.get('name'),
            'hash_key': gind.get('index_key_name'),
            'range_key': gind.get('index_sort_key_name'),
            'projection_type': gind.get('projection_type', 'ALL'),
            'write_capacity': gind.get('write_capacity', 1),
            'read_capacity': gind.get('read_capacity', 1),
            'non_key_attributes': gind.get('non_key_attributes'),
        }
        gl_index_definitions.append(index)

    lc_index_definitions = []
    for loc_ind in local_indexes:
        index = {
            'name': loc_ind.get('name'),
            'range_key': loc_ind.get('index_sort_key_name'),
            'projection_type': loc_ind.get('projection_type', 'ALL'),
            'non_key_attributes': loc_ind.get('non_key_attributes')
        }
        lc_index_definitions.append(index)

    table_content = {
        "name": table_name,
        "hash_key": hash_key,
        "range_key": range_key,
        "read_capacity": read_capacity,
        "write_capacity": write_capacity,
        "global_secondary_index": gl_index_definitions,
        "local_secondary_index": lc_index_definitions,
        "attribute": attributes
    }

    if stream_view_type:
        table_content.update({'stream_enabled': 'true'})
        table_content.update({'stream_view_type': stream_view_type})

    resource = {
        table_name: table_content
    }
    return resource


def dynamodb_scalable_target(tf_target_resource_name, resource_id,
                             scalable_dimension,
                             min_capacity=None,
                             max_capacity=None,
                             role_name=None):
    target = {
        "scalable_dimension": scalable_dimension,
        "service_namespace": 'dynamodb',
        'resource_id': resource_id
    }

    if min_capacity:
        target['max_capacity'] = int(min_capacity)
    if max_capacity:
        target['min_capacity'] = int(max_capacity)
    if role_name:
        target['role_arn'] = build_role_arn_ref(role_name=role_name)

    resource = {
        tf_target_resource_name: target
    }
    return resource


def dynamo_db_autoscaling_target_policy(target_value,
                                        target_name,
                                        tf_resource_name,
                                        predefined_metric_type=None,
                                        resource_label=None,
                                        metric_name=None, namespace=None,
                                        dimensions=None, statistic=None,
                                        unit=None, scale_out_cooldown=None,
                                        scale_in_cooldown=None):
    resource_id = build_aws_appautoscaling_target_resource_id_ref(
        target_name=target_name)
    scalable_dimension = build_aws_appautoscaling_target_scalable_dimension_ref(
        target_name=target_name)
    service_namespace = build_aws_appautoscaling_target_service_namespace_ref(
        target_name=target_name)

    resource = {
        'name': f'dynamodb-read-capacity-utilization-{resource_id}',
        'policy_type': 'TargetTrackingScaling',
        'resource_id': resource_id,
        'scalable_dimension': scalable_dimension,
        'service_namespace': service_namespace,
    }

    target_scaling_config_dict = dict()
    if target_value:
        target_scaling_config_dict['target_value'] = target_value
    predefined_config_dict = dict()
    if predefined_metric_type:
        predefined_config_dict[
            'predefined_metric_type'] = predefined_metric_type
    if resource_label:
        predefined_config_dict['resource_label'] = resource_label
    if predefined_config_dict:
        target_scaling_config_dict[
            'predefined_metric_specification'] = predefined_config_dict

    customized_config_dict = dict()
    if metric_name:
        customized_config_dict['metric_name'] = metric_name
    if namespace:
        customized_config_dict['namespace'] = namespace
    if dimensions:
        customized_config_dict['dimensions'] = dimensions
    if statistic:
        customized_config_dict['statistic'] = statistic
    if unit:
        customized_config_dict['unit'] = unit
    if customized_config_dict:
        target_scaling_config_dict[
            'customized_metric_specification'] = customized_config_dict

    if scale_out_cooldown:
        target_scaling_config_dict['scale_out_cooldown'] = scale_out_cooldown
    if scale_in_cooldown:
        target_scaling_config_dict['scale_in_cooldown'] = scale_in_cooldown
    if target_scaling_config_dict:
        resource[
            'target_tracking_scaling_policy_configuration'] = target_scaling_config_dict

    resource = {
        tf_resource_name: resource
    }
    return resource
