#  Copyright 2021 EPAM Systems, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import json

from syndicate.commons.log_helper import get_logger
from syndicate.connection.iam_connection import build_trusted_relationships
from syndicate.core.transform.build_meta_transformer import \
    BuildMetaTransformer
from syndicate.core.transform.terraform.static_content.terraform_transformer_content import \
    generate_tf_template_for_lambda, generate_tf_template_for_iam_role, \
    generate_tf_template_for_iam_policy, generate_tf_template_for_dynamo_table, \
    get_api_gateway_resource, get_api_gateway_method, \
    generate_tf_template_for_api_gateway_api, \
    get_dynamo_db_autoscaling_read_target, \
    get_dynamo_db_autoscaling_read_policy, \
    get_dynamo_db_autoscaling_write_target, \
    get_dynamo_db_autoscaling_write_policy, api_gateway_method_response, \
    api_gateway_integration, api_gateway_integration_response, \
    api_gateway_stage, api_gateway_deployment

AVAILABLE_METHODS = ['GET', 'PUT', 'POST', 'OPTIONS', 'DELETE',
                     'HEAD', 'PATCH', 'ANY']

READ_CAPACITY_UNITS = 'ReadCapacityUnits'
WRITE_CAPACITY_UNITS = 'WriteCapacityUnits'

_LOG = get_logger('syndicate.core.transform.terraform_transformer')


class TerraformTransformer(BuildMetaTransformer):

    def add_resource(self, transformed_resource):
        pass  # TODO implement or design other approach

    def output_file_name(self) -> str:
        return 'terraform_template.tf.json'

    def _transform_iam_managed_policy(self, name, resource):
        policy = resource.get('policy_content')
        policy_content = json.dumps(policy)

        return generate_tf_template_for_iam_policy(policy_name=name,
                                                   content=policy_content)

    def _transform_iam_role(self, name, resource):
        custom_policies = resource.get('custom_policies', [])
        predefined_policies = resource.get('predefined_policies', [])
        policies = set(custom_policies + predefined_policies)
        allowed_accounts = resource.get('allowed_accounts', [])
        principal_service = resource.get('principal_service')
        external_id = resource.get('external_id')
        trust_rltn = resource.get('trusted_relationships')

        assume_role_policy = build_trusted_relationships(
            trusted_relationships=trust_rltn, external_id=external_id,
            allowed_service=principal_service,
            allowed_account=allowed_accounts)

        return generate_tf_template_for_iam_role(role_name=name,
                                                 managed_policies=policies,
                                                 assume_role_policy=json.dumps(
                                                     assume_role_policy))

    def _transform_lambda(self, name, resource):
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

        return generate_tf_template_for_lambda(lambda_name=name,
                                               function_name=name,
                                               runtime=runtime,
                                               role_name=iam_role_name,
                                               handler=function_name,
                                               file_name=file_name,
                                               memory=memory,
                                               timeout=timeout,
                                               env_variables=env_variables)

    def _transform_dynamo_db_table(self, name, resource):
        deploy_resources = []

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
        deploy_resources.append(dynamo_db_template)

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
                deploy_resources.append(read_target)
                deploy_resources.append(read_policy)
            elif mode == WRITE_CAPACITY_UNITS:
                write_target_target_name = f'dynamo_db_{name}_write_target'
                write_target = get_dynamo_db_autoscaling_write_target(
                    autoscaling_write_target=write_target_target_name,
                    max_capacity=max_capacity, min_capacity=min_capacity,
                    table_name=name)
                write_policy = get_dynamo_db_autoscaling_write_policy(
                    autoscaling_write_target=write_target_target_name,
                    target_value=target_utilization)
                deploy_resources.append(write_target)
                deploy_resources.append(write_policy)
        return deploy_resources

    def _transform_s3_bucket(self, name, resource):
        location = resource.get('location')
        acl = resource.get('acl')
        policy = resource.get('policy')

        pass

    def _transform_cloud_watch_rule(self, name, resource):
        rule_type = resource.get('rule_type')
        expression = resource.get('expression')
        region = resource.get('region')

        pass

    def _transform_api_gateway(self, name, resource):
        deploy_resources = []
        api_name = resource.get('resource_name')
        authorizers = resource.get('authorizers')
        dependencies = resource.get('dependencies')
        auth_type = authorizers.get('type')
        lambda_name = authorizers.get('lambda_name')
        ttl = authorizers.get('ttl')

        deploy_stage = resource.get('deploy_stage')
        if deploy_stage:
            deployment_name = f'{deploy_stage}_deployment'
            deployment = api_gateway_deployment(api_name=api_name,
                                                deployment_name=deployment_name)
            stage = api_gateway_stage(api_name=api_name,
                                      stage_name=deploy_stage,
                                      deployment_name=deployment_name)
            deploy_resources.append(stage)
            deploy_resources.append(deployment)

        rest_api_template = generate_tf_template_for_api_gateway_api(
            api_name=api_name)
        deploy_resources.append(rest_api_template)

        resources = resource.get('resources')
        for res_name, res in resources.items():
            resource = get_api_gateway_resource(path_part=res_name,
                                                rest_api=api_name)
            deploy_resources.append(resource)
            for http_method in AVAILABLE_METHODS:
                method_config = res.get(http_method)
                if method_config:
                    resource_name = res_name.replace('/', '')

                    method_name = f'{resource_name}-{http_method}'
                    method_template = get_api_gateway_method(
                        http_method=http_method,
                        resource_name=resource_name,
                        rest_api=api_name,
                        authorization='NONE',
                        method_name=method_name)
                    deploy_resources.append(method_template)

                    lambda_alias = method_config.get('lambda_alias')
                    authorization_type = method_config.get(
                        'authorization_type')
                    method_request_parameters = method_config.get(
                        'method_request_parameters')
                    lambda_name = method_config.get('lambda_name')
                    integration_type = method_config.get('integration_type')
                    integration_request_template = method_config.get(
                        'integration_request_body_template')

                    integration_name = f'{resource_name}_{http_method}_integration'
                    integration = api_gateway_integration(
                        integration_name=integration_name,
                        api_name=api_name,
                        http_method=http_method,
                        resource_name=resource_name,
                        integration_type='AWS',
                        lambda_name=lambda_name,
                        request_template=integration_request_template)
                    deploy_resources.append(integration)

                    responses = method_config.get('responses')
                    for response in responses:
                        status_code = response.get('status_code')
                        method_response = api_gateway_method_response(
                            resource_name=resource_name,
                            status_code=status_code,
                            api_name=api_name,
                            http_method=http_method,
                            method_name=method_name)
                        deploy_resources.append(method_response)

                    integration_responses = method_config.get(
                        'integration_responses')
                    for int_response in integration_responses:
                        status_code = int_response.get('status_code')
                        response_templates = int_response.get(
                            'response_templates')
                        error_regex = int_response.get('error_regex')
                        integration_response = api_gateway_integration_response(
                            resource_name=resource_name,
                            api_name=api_name,
                            status_code=status_code,
                            response_template=response_templates,
                            http_method=http_method,
                            method_name=method_name,
                            integration=integration_name,
                            selection_pattern=error_regex)
                        deploy_resources.append(integration_response)
        return deploy_resources

    def _transform_sns_topic(self, name, resource):
        deploy_stage = resource.get('deploy_stage')
        region = resource.get('region')
        event_sources = resource.get('event_sources')

        pass

    def _transform_cloudwatch_alarm(self, name, resource):
        metric_name = resource.get('metric_name')
        period = resource.get('period')
        evaluation_periods = resource.get('evaluation_periods')
        threshold = resource.get('threshold')
        comparison_operator = resource.get('comparison_operator')
        statistic = resource.get('statistic')
        sns_topics = resource.get('sns_topics')

        pass

    def _transform_ec2_instance(self, name, resource):
        metric_name = resource.get('metric_name')
        period = resource.get('period')
        evaluation_periods = resource.get('evaluation_periods')
        threshold = resource.get('threshold')
        comparison_operator = resource.get('comparison_operator')
        statistic = resource.get('statistic')
        sns_topics = resource.get('sns_topics')

        pass

    def _transform_sqs_queue(self, name, resource):
        pass

    def _transform_dynamodb_stream(self, name, resource):
        table_name = resource.get('table')
        stream_view_type = resource.get('stream_view_type')

        pass

    def _compose_template(self):
        meta = {'resource': self.resources}
        return json.dumps(meta)
