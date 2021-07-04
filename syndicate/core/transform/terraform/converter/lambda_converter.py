from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class LambdaConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        function_name = resource.get('func_name')
        iam_role_name = resource.get('iam_role_name')
        runtime = resource.get('runtime')
        memory = resource.get('memory')
        timeout = resource.get('timeout')
        s3_path = resource.get('s3_path')
        file_name = s3_path.split('/')[-1]
        env_variables = resource.get('env_variables')

        # TODO ?????? !!!!!
        log_expiration = resource.get('logs_expirations')
        concurrent_executions = resource.get('concurrent_executions')
        concurrency = resource.get('concurrency')

        aws_lambda = template_for_lambda(lambda_name=name,
                                         function_name=name,
                                         runtime=runtime,
                                         role_name=iam_role_name,
                                         handler=function_name,
                                         file_name=file_name,
                                         memory=memory,
                                         timeout=timeout,
                                         env_variables=env_variables)
        self.template.add_aws_lambda(meta=aws_lambda)


def template_for_lambda(lambda_name, role_name, handler, runtime,
                        function_name, file_name, memory, timeout,
                        env_variables):
    role_arn_exp = '${' + f'aws_iam_role.{role_name}.arn' + '}'
    variables = []
    if env_variables:
        variables = [{'variables': env_variables}]
    resource = {
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
    return resource
