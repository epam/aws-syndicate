from syndicate.connection.cloud_watch_connection import \
    get_lambda_log_group_name
from syndicate.core.resources.lambda_resource import LAMBDA_MAX_CONCURRENCY, \
    PROVISIONED_CONCURRENCY
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_ref_to_lambda_layer_arn, build_function_arn_ref, build_role_arn_ref, \
    build_function_name_ref, build_lambda_version_ref, \
    build_lambda_alias_name_ref


class LambdaConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        function_name = resource.get('func_name')
        iam_role_name = resource.get('iam_role_name')
        runtime = resource.get('runtime')
        memory = resource.get('memory')
        timeout = resource.get('timeout')
        env_variables = resource.get('env_variables')
        publish_version = resource.get('publish_version', False)
        subnet_ids = resource.get('subnet_ids', [])
        security_group_ids = resource.get('security_group_ids', [])

        s3_path = resource.get('s3_path')
        s3_bucket = self.config.deploy_target_bucket

        lambda_layers_arns = []
        layer_meta = resource.get('layers')
        if layer_meta:
            for layer_name in layer_meta:
                layer_ref = build_ref_to_lambda_layer_arn(
                    layer_name=layer_name)
                lambda_layers_arns.append(layer_ref)

        retention = resource.get('logs_expiration')
        if retention:
            log_group = cloud_watch_log_group(lambda_name=function_name,
                                              retention=retention)
            self.template.add_cloud_watch_log_group(meta=log_group)

        reserved_concur = resource.get(LAMBDA_MAX_CONCURRENCY)
        lambda_service = self.resources_provider.lambda_resource()
        if not lambda_service.check_concurrency_availability(reserved_concur):
            reserved_concur = None

        aws_lambda = template_for_lambda(lambda_name=name,
                                         function_name=name,
                                         runtime=runtime,
                                         role_name=iam_role_name,
                                         handler=function_name,
                                         memory=memory,
                                         timeout=timeout,
                                         env_variables=env_variables,
                                         publish=publish_version,
                                         subnet_ids=subnet_ids,
                                         security_group_ids=security_group_ids,
                                         reserved_concurrent_executions=reserved_concur,
                                         s3_bucket=s3_bucket,
                                         s3_key=s3_path)
        self.template.add_aws_lambda(meta=aws_lambda)

        self.configure_concurrency(resource=resource,
                                   function_name=name)

    def configure_concurrency(self, resource, function_name):
        provisioned_concur = resource.get(PROVISIONED_CONCURRENCY)
        publish_version = resource.get('publish_version', False)
        if publish_version:
            if provisioned_concur:
                res_name = 'concurrency_config_version'
                concurrency = provisioned_concurrency_config_with_lambda_version(
                    name=res_name,
                    function_name=function_name,
                    provisioned_concur=provisioned_concur)
                self.template.add_aws_lambda_provisioned_concurrency_config(
                    meta=concurrency)
        alias = resource.get('alias')
        if alias:
            alias_resource_name = f'{function_name}_{alias}'
            alias_template = template_for_alias(alias_name=alias,
                                                resource_name=alias_resource_name,
                                                function_name=function_name)
            self.template.add_aws_lambda_alias(meta=alias_template)

            if provisioned_concur:
                res_name = 'concurrency_config_alias'
                concurrency = provisioned_concurrency_config_with_lambda_alias(
                    name=res_name, function_name=function_name,
                    provisioned_concur=provisioned_concur,
                    alias_name=alias_resource_name)
                self.template.add_aws_lambda_provisioned_concurrency_config(
                    meta=concurrency)


def cloud_watch_log_group(lambda_name, retention):
    name = get_lambda_log_group_name(lambda_name=lambda_name)
    resource = {
        "log": {
            "name": name,
            "retention_in_days": retention
        }
    }
    return resource


def provisioned_concurrency_config_with_lambda_version(name, function_name,
                                                       provisioned_concur):
    function_name_ref = build_function_name_ref(function_name=function_name)
    version_ref = build_lambda_version_ref(function_name=function_name)
    resource = {
        name: {
            "function_name": function_name_ref,
            "provisioned_concurrent_executions": provisioned_concur[
                'value'],
            "qualifier": version_ref
        }
    }
    return resource


def provisioned_concurrency_config_with_lambda_alias(name, function_name,
                                                     provisioned_concur,
                                                     alias_name):
    function_name_ref = build_function_name_ref(function_name=function_name)
    alias_name_ref = build_lambda_alias_name_ref(alias_name=alias_name)
    resource = {
        name: {
            "function_name": function_name_ref,
            "provisioned_concurrent_executions": provisioned_concur[
                'value'],
            "qualifier": alias_name_ref
        }
    }
    return resource


def template_for_alias(resource_name, alias_name, function_name):
    function_ref = build_function_arn_ref(function_name=function_name)
    function_version = build_lambda_version_ref(function_name=function_name)
    resource = {
        resource_name: {
            'name': alias_name,
            'function_name': function_ref,
            'function_version': function_version
        }
    }
    return resource


def template_for_lambda(lambda_name, role_name, handler, runtime,
                        function_name, subnet_ids, security_group_ids,
                        s3_key=None,
                        s3_bucket=None,
                        memory=None,
                        timeout=None,
                        env_variables=None, layers=None, publish=False,
                        reserved_concurrent_executions=None,
                        tracing_mode=None):
    role_arn_exp = build_role_arn_ref(role_name=role_name)

    lambda_res = {
        'function_name': function_name,
        'role': role_arn_exp,
        'runtime': runtime,
        'handler': handler,
        'publish': publish
    }

    if subnet_ids and security_group_ids:
        vpc_config = {
            'subnet_ids': subnet_ids,
            'security_group_ids': security_group_ids
        }
        lambda_res['vpc_config'] = vpc_config

    if s3_key and s3_bucket:
        lambda_res['s3_key'] = s3_key
        lambda_res['s3_bucket'] = s3_bucket
    if memory:
        lambda_res['memory_size'] = memory
    if timeout:
        lambda_res['timeout'] = timeout
    if env_variables:
        lambda_res['environment'] = [{'variables': env_variables}]
    if layers:
        lambda_res['layers'] = layers
    if reserved_concurrent_executions:
        lambda_res[
            'reserved_concurrent_executions'] = reserved_concurrent_executions
    if tracing_mode:
        lambda_res['tracing_config'] = {'mode': tracing_mode}
    if reserved_concurrent_executions:
        lambda_res[
            'reserved_concurrent_executions'] = reserved_concurrent_executions

    resource = {lambda_name: lambda_res}
    return resource
