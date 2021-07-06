def build_function_name_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.function_name}'


def build_function_arn_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.arn}'


def build_lambda_alias_name_ref(alias_name):
    return '${aws_lambda_alias.' + alias_name + '.name}'


def build_lambda_version_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.version}'


def build_function_invoke_arn_ref(function_name):
    return '${aws_lambda_function.' + function_name + '.invoke_arn}'


def build_authorizer_id_ref(authorizer_name):
    return '${aws_api_gateway_authorizer.' + authorizer_name + '.id}'


def build_method_name_reference(method_name):
    return '${aws_api_gateway_method.' + method_name + '.http_method}'


def build_resource_id_ref(resource_name):
    return '${aws_api_gateway_resource.' + resource_name + '.id}'


def build_rest_api_id_ref(api_name):
    return '${aws_api_gateway_rest_api.' + api_name + '.id}'


def build_sns_topic_arn_ref(sns_topic):
    return '${aws_sns_topic.' + sns_topic + '.arn}'


def build_api_gateway_root_resource_id_ref(api_name):
    return '${aws_api_gateway_rest_api.' + api_name + '.root_resource_id}'


def build_api_gateway_deployment_id_ref(deployment_name):
    return '${aws_api_gateway_deployment.' + deployment_name + '.id}'


def build_cognito_identity_pool_id(pool_name):
    return '${aws_cognito_identity_pool.' + pool_name + '.id'


def build_iam_role_arn_ref(role_name):
    return '${aws_iam_role.' + role_name + '.arn'


def build_ref_to_lambda_layer_arn(layer_name):
    return '${aws_lambda_layer_version.' + layer_name + '.arn'


def build_role_arn_ref(role_name):
    return '${aws_iam_role.' + role_name + '.arn}'
