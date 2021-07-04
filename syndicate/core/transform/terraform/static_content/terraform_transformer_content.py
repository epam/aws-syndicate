def generate_tf_template_for_lambda(lambda_name, role_name, handler, runtime,
                                    function_name, file_name, memory, timeout,
                                    env_variables):
    role_arn_exp = '${' + f'aws_iam_role.{role_name}.arn' + '}'
    variables = []
    if env_variables:
        variables = [{'variables': env_variables}]
    resource = {
        "aws_lambda_function": [
            {
                lambda_name: {
                    "filename": file_name,
                    "role": role_arn_exp,
                    "handler": handler,
                    "runtime": runtime,
                    "function_name": function_name,
                    "memory_size": memory,
                    "timeout": timeout,
                    "environment": variables
                }
            }
        ]
    }
    return resource


def generate_tf_template_for_iam_role(role_name,
                                      managed_policies,
                                      assume_role_policy):
    policy_arns_exp = []
    for policy in managed_policies:
        policy_arn = f'aws_iam_policy.{policy}.arn'
        policy_exp = "${" + policy_arn + "}"
        policy_arns_exp.append(policy_exp)
    resource = {
        "aws_iam_role": [
            {
                role_name: {
                    "assume_role_policy": assume_role_policy,
                    "name": role_name,
                    "managed_policy_arns": policy_arns_exp
                }
            }
        ]
    }
    return resource


def generate_tf_template_for_iam_policy(policy_name, content):
    resource = {
        "aws_iam_policy": [
            {
                policy_name: [
                    {
                        "name": policy_name,
                        "policy": content
                    }
                ]
            }
        ]
    }
    return resource


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
        "aws_dynamodb_table": [
            {
                table_name: [
                    {
                        "name": table_name,
                        "hash_key": hash_key,
                        "range_key": range_key,
                        "read_capacity": read_capacity,
                        "write_capacity": write_capacity,
                        "global_secondary_index": g_index,
                        "attribute": attributes
                    }
                ]
            }
        ]
    }
    return resource


def get_autoscaling_for_table():
    resource = {
        "aws_appautoscaling_target": [
            {
                "dynamodb_table_read_target": [
                    {
                        "max_capacity": 100,
                        "min_capacity": 5,
                        "resource_id": "table/tableName",
                        "scalable_dimension": "dynamodb:table:ReadCapacityUnits",
                        "service_namespace": "dynamodb"
                    }
                ]
            }
        ]
    }
    return resource


def get_dynamo_db_autoscaling_read_target(autoscaling_read_target, table_name,
                                          max_capacity, min_capacity):
    table_name_regex = "${aws_dynamodb_table." + table_name + ".name}"
    resource = {
        "aws_appautoscaling_target": [
            {
                autoscaling_read_target: [
                    {
                        "max_capacity": max_capacity,
                        "min_capacity": min_capacity,
                        "resource_id": f"table/{table_name_regex}",
                        "scalable_dimension": "dynamodb:table:ReadCapacityUnits",
                        "service_namespace": "dynamodb"
                    }
                ]
            }
        ]
    }
    return resource


def get_dynamo_db_autoscaling_write_target(autoscaling_write_target,
                                           table_name, max_capacity,
                                           min_capacity):
    table_name_regex = "${aws_dynamodb_table." + table_name + ".name}"
    resource = {
        "aws_appautoscaling_target": [
            {
                autoscaling_write_target: [
                    {
                        "max_capacity": max_capacity,
                        "min_capacity": min_capacity,
                        "resource_id": f"table/{table_name_regex}",
                        "scalable_dimension": "dynamodb:table:WriteCapacityUnits",
                        "service_namespace": "dynamodb"
                    }
                ]
            }
        ]
    }
    return resource


def get_dynamo_db_autoscaling_read_policy(autoscaling_read_target,
                                          target_value):
    resource_id = '${aws_appautoscaling_target.' + autoscaling_read_target + '.resource_id}'
    scalable_dimension = '${aws_appautoscaling_target.' + autoscaling_read_target + '.scalable_dimension}'
    service_namespace = '${aws_appautoscaling_target.' + autoscaling_read_target + '.service_namespace}'
    resource = {
        "aws_appautoscaling_policy": [
            {
                "dynamodb-test-table_read_policy": [
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
                ]
            }
        ]
    }
    return resource


def get_dynamo_db_autoscaling_write_policy(autoscaling_write_target,
                                           target_value):
    resource_id = '${aws_appautoscaling_target.' + autoscaling_write_target + '.resource_id}'
    scalable_dimension = '${aws_appautoscaling_target.' + autoscaling_write_target + '.scalable_dimension}'
    service_namespace = '${aws_appautoscaling_target.' + autoscaling_write_target + '.service_namespace}'
    resource = {
        "aws_appautoscaling_policy": [
            {
                "dynamodb-test-table_write_policy": [
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
                ]
            }
        ]
    }
    return resource


def generate_tf_template_for_api_gateway_api(api_name):
    resource = {
        "aws_api_gateway_rest_api": [
            {
                api_name: [
                    {
                        "endpoint_configuration": [
                            {
                                "types": [
                                    "REGIONAL"
                                ]
                            }
                        ],
                        "name": api_name
                    }
                ]
            }
        ]
    }
    return resource


def get_api_gateway_resource(path_part, rest_api):
    resource_name = path_part.replace('/', '')
    parent_id = '${aws_api_gateway_rest_api.' + rest_api + '.root_resource_id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
    resource = {
        "aws_api_gateway_resource": [
            {
                resource_name: [
                    {
                        "parent_id": parent_id,
                        "path_part": resource_name,
                        "rest_api_id": rest_api_id
                    }
                ]
            }
        ]
    }
    return resource


def api_gateway_method_response(method_name, status_code, http_method,
                                resource_name, api_name):
    response_name = f'{resource_name}_{http_method}_{status_code}_method_response'
    method = '${aws_api_gateway_method.' + method_name + '.http_method}'
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
    resource = {
        "aws_api_gateway_method_response": [
            {
                response_name: [
                    {
                        "http_method": method,
                        "resource_id": resource_id,
                        "rest_api_id": rest_api_id,
                        "status_code": status_code
                    }
                ]
            }
        ]
    }
    return resource


def api_gateway_integration(integration_name, api_name, resource_name,
                            http_method, integration_type, lambda_name,
                            request_template):
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
    uri = '${aws_lambda_function.' + lambda_name + '.invoke_arn}'
    resource = {
        "aws_api_gateway_integration": [
            {
                integration_name: [
                    {
                        "http_method": http_method,
                        "resource_id": resource_id,
                        "rest_api_id": rest_api_id,
                        "type": integration_type,
                        "integration_http_method": 'POST',
                        "uri": uri,
                        "request_templates": request_template
                    }
                ]
            }
        ]
    }
    return resource


def api_gateway_stage(api_name, stage_name, deployment_name):
    rest_api_id = "${aws_api_gateway_rest_api." + api_name + ".id}"
    deployment_name = '${aws_api_gateway_deployment.' + deployment_name + '.id}'
    resource = {
        "aws_api_gateway_stage": [
            {
                stage_name: [
                    {
                        "deployment_id": deployment_name,
                        "rest_api_id": rest_api_id,
                        "stage_name": stage_name
                    }
                ]
            }
        ]
    }
    return resource


def api_gateway_deployment(api_name, deployment_name):
    rest_api_id = "${aws_api_gateway_rest_api." + api_name + ".id}"
    resource = {
        "aws_api_gateway_deployment": [
            {
                deployment_name: [
                    {
                        "rest_api_id": rest_api_id
                    }
                ]
            }
        ]
    }
    return resource


def api_gateway_integration_response(resource_name, api_name,
                                     status_code, response_template,
                                     http_method, method_name, integration,
                                     selection_pattern=None):
    integration_response_name = f'{resource_name}_{http_method}_{status_code}_integration_response'
    method = '${aws_api_gateway_method.' + method_name + '.http_method}'
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + api_name + '.id}'
    resource = {
        "aws_api_gateway_integration_response": [
            {
                integration_response_name: [
                    {
                        "http_method": method,
                        "resource_id": resource_id,
                        "response_templates": response_template,
                        "rest_api_id": rest_api_id,
                        "status_code": status_code,
                        "selection_pattern": selection_pattern,
                        "depends_on": [
                            f'aws_api_gateway_integration.{integration}']
                    }
                ]
            }
        ]
    }
    return resource


def get_api_gateway_method(http_method, resource_name, rest_api,
                           method_name,
                           authorization='NONE'):
    resource_id = '${aws_api_gateway_resource.' + resource_name + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
    resource = {
        "aws_api_gateway_method": [
            {
                method_name: [
                    {
                        "authorization": authorization,
                        "http_method": http_method,
                        "resource_id": resource_id,
                        "rest_api_id": rest_api_id
                    }
                ]
            }
        ]

    }
    return resource


def get_api_gateway_stage(stage_name, deployment, rest_api):
    deployment_id = '${aws_api_gateway_deployment.' + deployment + '.id}'
    rest_api_id = '${aws_api_gateway_rest_api.' + rest_api + '.id}'
    resource = {
        {
            "aws_api_gateway_stage": [
                {
                    stage_name: [
                        {
                            "deployment_id": deployment_id,
                            "rest_api_id": rest_api_id,
                            "stage_name": stage_name
                        }
                    ]
                }
            ]
        }
    }
    return resource
