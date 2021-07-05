from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter

READ_CAPACITY_UNITS = 'ReadCapacityUnits'
WRITE_CAPACITY_UNITS = 'WriteCapacityUnits'


class DynamoDbConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        hash_key_name = resource.get('hash_key_name')
        hash_key_type = resource.get('hash_key_type')
        sort_key_name = resource.get('sort_key_name')
        sort_key_type = resource.get('sort_key_type')
        read_capacity = resource.get('read_capacity', 1)
        write_capacity = resource.get('write_capacity', 1)
        global_indexes = resource.get('global_indexes')
        external = resource.get('external')

        dynamo_db_template = generate_tf_template_for_dynamo_table(
            hash_key=hash_key_name,
            hash_key_type=hash_key_type,
            range_key=sort_key_name,
            range_key_type=sort_key_type,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            global_index=global_indexes,
            table_name=name)
        self.template.add_aws_dynamodb_table(meta=dynamo_db_template)

        autoscaling = resource.get('autoscaling', [])
        for aut in autoscaling:
            max_capacity = aut.get('max_capacity')
            min_capacity = aut.get('min_capacity')
            dimension = aut.get('dimension')
            target_utilization = aut.get('config').get('target_utilization')

            mode = dimension.split(':')[-1]
            if mode == READ_CAPACITY_UNITS:
                read_target_name = f'dynamo_db_{name}_read_target'
                read_target = get_dynamo_db_autoscaling_read_target(
                    autoscaling_read_target=read_target_name, table_name=name,
                    max_capacity=max_capacity, min_capacity=min_capacity)
                read_policy = get_dynamo_db_autoscaling_read_policy(
                    autoscaling_read_target=read_target_name,
                    target_value=target_utilization)
                self.template.add_aws_appautoscaling_target(meta=read_target)
                self.template.add_aws_appautoscaling_policy(meta=read_policy)
            elif mode == WRITE_CAPACITY_UNITS:
                write_target_target_name = f'dynamo_db_{name}_write_target'
                write_target = get_dynamo_db_autoscaling_write_target(
                    autoscaling_write_target=write_target_target_name,
                    max_capacity=max_capacity, min_capacity=min_capacity,
                    table_name=name)
                write_policy = get_dynamo_db_autoscaling_write_policy(
                    autoscaling_write_target=write_target_target_name,
                    target_value=target_utilization)
                self.template.add_aws_appautoscaling_target(meta=write_target)
                self.template.add_aws_appautoscaling_policy(meta=write_policy)


def generate_tf_template_for_dynamo_table(table_name, hash_key, hash_key_type,
                                          range_key, range_key_type,
                                          read_capacity, write_capacity,
                                          global_index):
    attributes = [{'name': hash_key,
                   'type': hash_key_type}]
    if range_key:
        attributes.append({'name': range_key,
                           'type': range_key_type})
    for index in global_index:
        index_key_name = index.get('index_key_name')
        if index_key_name not in [hash_key, range_key]:
            index_key_type = index.get('index_key_type')
            attributes.append({'name': index_key_name,
                               'type': index_key_type})

        index_sort_key_name = index.get('index_sort_key_name')
        if index_sort_key_name and index_sort_key_name not in [hash_key,
                                                               range_key]:
            index_sort_key_type = index.get('index_sort_key_type')
            attributes.append({'name': index_sort_key_name,
                               'type': index_sort_key_type})

    g_index = []
    for gind in global_index:
        index = {
            'name': gind.get('name'),
            'hash_key': gind.get('index_key_name'),
            'range_key': gind.get('index_sort_key_name'),
            'projection_type': gind.get('projection_type'),
            'write_capacity': gind.get('write_capacity', 1),
            'read_capacity': gind.get('read_capacity', 1)
        }
        g_index.append(index)

    resource = {
        table_name:
            {
                "name": table_name,
                "hash_key": hash_key,
                "range_key": range_key,
                "read_capacity": read_capacity,
                "write_capacity": write_capacity,
                "global_secondary_index": g_index,
                "attribute": attributes
            }
    }
    return resource


def get_dynamo_db_autoscaling_read_target(autoscaling_read_target, table_name,
                                          max_capacity, min_capacity):
    table_name_regex = "${aws_dynamodb_table." + table_name + ".name}"
    resource = {
        autoscaling_read_target:
            {
                "max_capacity": max_capacity,
                "min_capacity": min_capacity,
                "resource_id": f"table/{table_name_regex}",
                "scalable_dimension": "dynamodb:table:ReadCapacityUnits",
                "service_namespace": "dynamodb"
            }
    }
    return resource


def get_dynamo_db_autoscaling_write_target(autoscaling_write_target,
                                           table_name, max_capacity,
                                           min_capacity):
    table_name_regex = "${aws_dynamodb_table." + table_name + ".name}"
    resource = {
        autoscaling_write_target:
            {
                "max_capacity": max_capacity,
                "min_capacity": min_capacity,
                "resource_id": f"table/{table_name_regex}",
                "scalable_dimension": "dynamodb:table:WriteCapacityUnits",
                "service_namespace": "dynamodb"
            }
    }

    return resource


def get_dynamo_db_autoscaling_read_policy(autoscaling_read_target,
                                          target_value):
    resource_id = '${aws_appautoscaling_target.' + autoscaling_read_target + '.resource_id}'
    scalable_dimension = '${aws_appautoscaling_target.' + autoscaling_read_target + '.scalable_dimension}'
    service_namespace = '${aws_appautoscaling_target.' + autoscaling_read_target + '.service_namespace}'
    resource = {
        "dynamodb-test-table_read_policy":
            {
                "name": f"dynamodb-read-capacity-utilization-{resource_id}",
                "policy_type": "TargetTrackingScaling",
                "resource_id": resource_id,
                "scalable_dimension": scalable_dimension,
                "service_namespace": service_namespace,
                "target_tracking_scaling_policy_configuration": [
                    {
                        "predefined_metric_specification": [
                            {
                                "predefined_metric_type": "DynamoDBReadCapacityUtilization"
                            }
                        ],
                        "target_value": target_value
                    }
                ]
            }
    }

    return resource


def get_dynamo_db_autoscaling_write_policy(autoscaling_write_target,
                                           target_value):
    resource_id = '${aws_appautoscaling_target.' + autoscaling_write_target + '.resource_id}'
    scalable_dimension = '${aws_appautoscaling_target.' + autoscaling_write_target + '.scalable_dimension}'
    service_namespace = '${aws_appautoscaling_target.' + autoscaling_write_target + '.service_namespace}'
    resource = {
        "dynamodb-test-table_write_policy":
            {
                "name": f"dynamodb-write-capacity-utilization-{resource_id}",
                "policy_type": "TargetTrackingScaling",
                "resource_id": resource_id,
                "scalable_dimension": scalable_dimension,
                "service_namespace": service_namespace,
                "target_tracking_scaling_policy_configuration": [
                    {
                        "predefined_metric_specification": [
                            {
                                "predefined_metric_type": "DynamoDBWriteCapacityUtilization"
                            }
                        ],
                        "target_value": target_value
                    }
                ]
            }
    }
    return resource
