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
import json

from syndicate.commons.log_helper import get_logger
from syndicate.core.resources.batch_compenv_resource import DEFAULT_STATE
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_resource_name_builder import \
    build_terraform_resource_name
from syndicate.core.transform.terraform.tf_resource_reference_builder import \
    build_role_name_ref, build_instance_profile_arn_ref, build_role_arn_ref

_LOG = get_logger('syndicate.core.transform.terraform'
                  '.converter.tf_batch_compenv_converter')

ECS_POLICY_ARN = 'arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role'
BATCH_SERVICE_ROLE = 'arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole'
AWS_BATCH_SERVICE_ROLE = 'AWSBatchServiceRole'


class BatchComputeEnvConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        state = resource.get('state')
        if not state:
            state = DEFAULT_STATE

        service_role_arn = self.service_role_arn(resource_meta=resource)

        env_type = resource.get('compute_environment_type')
        compute_resources = resource.get('compute_resources', {})
        res_type = compute_resources.get('type')
        minv_cpus = compute_resources.get('minv_cpus')
        desired_vcpus = compute_resources.get('desired_vcpus')
        maxv_cpus = compute_resources.get('maxv_cpus')
        instance_types = compute_resources.get('instance_types', [])
        security_group_ids = compute_resources.get('security_group_ids', [])
        subnets = compute_resources.get('subnets', [])

        instance_role = compute_resources.get('instance_role')
        if instance_role:
            ecs_policy_attachment = aws_iam_role_policy_attachment(
                role_name=instance_role, policy_arn=ECS_POLICY_ARN)
            self.template.add_aws_iam_role_policy_attachment(
                meta=ecs_policy_attachment)

        profile_name = f'{instance_role}_instance_profile'
        profile = aws_iam_instance_profile(role_name=instance_role,
                                           profile_name=profile_name)
        self.template.add_aws_iam_instance_profile(meta=profile)

        aws_batch_compute_environment = batch_com_env(
            compute_environment_name=name, env_type=env_type, state=state,
            service_role=service_role_arn,
            res_type=res_type,
            maxv_cpus=maxv_cpus,
            desired_vcpus=desired_vcpus, minv_cpus=minv_cpus,
            instance_types=instance_types,
            security_group_ids=security_group_ids, subnets=subnets,
            instance_profile_name=profile_name)

        self.template.add_aws_batch_compute_environment(
            meta=aws_batch_compute_environment)

    def service_role_arn(self, resource_meta):
        service_role = resource_meta.get('service_role')
        if not service_role:
            role = self.template.get_resource_by_name(AWS_BATCH_SERVICE_ROLE)
            if not role:
                batch_service_role = aws_batch_service_role(
                    AWS_BATCH_SERVICE_ROLE)
                self.template.add_aws_iam_role(meta=batch_service_role)
                batch_service_role_policy_attachment = aws_iam_role_policy_attachment(
                    role_name=AWS_BATCH_SERVICE_ROLE,
                    policy_arn=BATCH_SERVICE_ROLE)
                self.template.add_aws_iam_role_policy_attachment(
                    batch_service_role_policy_attachment)
                return build_role_arn_ref(AWS_BATCH_SERVICE_ROLE)
        role = self.template.get_resource_by_name(service_role)
        if not role:
            raise AssertionError("IAM role '{}' is not present "
                                 "in build meta.".format(service_role))
        return build_role_arn_ref(role_name=role)


def aws_batch_service_role(role_name):
    policy_content = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "batch.amazonaws.com"
                }
            }
        ]
    }
    resource = {
        role_name: {
            "name": role_name,
            "assume_role_policy": json.dumps(policy_content)
        }
    }
    return resource


def aws_iam_role_policy_attachment(role_name, policy_arn):
    resource = {
        build_terraform_resource_name(role_name, 'policy_attachment'):
            {
                "policy_arn": policy_arn,
                "role": build_role_name_ref(role_name)
            }
    }
    return resource


def aws_iam_instance_profile(profile_name, role_name):
    resource = {
        profile_name: {
            "name": role_name,
            "role": build_role_name_ref(role_name)
        }
    }
    return resource


def batch_com_env(compute_environment_name, env_type, service_role, state,
                  res_type=None, minv_cpus=None, desired_vcpus=None,
                  maxv_cpus=None,
                  instance_types=None, security_group_ids=None, subnets=None,
                  instance_profile_name=None):
    params = {
        'compute_environment_name': compute_environment_name,
        'type': env_type,
        'state': state,
        'service_role': service_role
    }

    comp_resources = dict()
    if res_type:
        comp_resources['type'] = res_type
    if minv_cpus:
        comp_resources['max_vcpus'] = minv_cpus
    if maxv_cpus:
        comp_resources['max_vcpus'] = maxv_cpus
    if desired_vcpus:
        comp_resources['desired_vcpus'] = desired_vcpus
    if instance_types:
        comp_resources['instance_type'] = instance_types
    if security_group_ids:
        comp_resources['security_group_ids'] = security_group_ids
    if subnets:
        comp_resources['subnets'] = subnets
    if instance_profile_name:
        comp_resources['instance_role'] = build_instance_profile_arn_ref(
            instance_profile_name=instance_profile_name)

    if comp_resources:
        params['compute_resources'] = comp_resources

    resource = {
        compute_environment_name: params
    }
    return resource
