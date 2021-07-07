from syndicate.core.resources.batch_compenv_resource import DEFAULT_STATE
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_role_arn_ref, build_role_name_ref

ECS_POLICY_ARN = 'arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role'


class BatchComputeEnvConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        state = resource.get('state')
        if not state:
            resource['state'] = DEFAULT_STATE

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

        profile = aws_iam_instance_profile(role_name=instance_role)
        self.template.add_aws_iam_instance_profile(meta=profile)
        policy_attachment = aws_iam_role_policy_attachment(
            role_name=instance_role)
        self.template.add_aws_iam_role_policy_attachment(
            meta=policy_attachment)

        aws_batch_compute_environment = batch_com_env(
            compute_environment_name=name, env_type=env_type, state=state,
            service_role='', res_type=res_type, maxv_cpus=maxv_cpus,
            desired_vcpus=desired_vcpus, minv_cpus=minv_cpus,
            instance_types=instance_types,
            security_group_ids=security_group_ids, subnets=subnets,
            instance_role=instance_role)

        self.template.add_aws_batch_compute_environment(
            meta=aws_batch_compute_environment)


def aws_iam_role_policy_attachment(role_name):
    resource = {
        f'{role_name}_policy_attachment':
            {
                "policy_arn": ECS_POLICY_ARN,
                "role": build_role_name_ref(role_name)
            }
    }
    return resource


def aws_iam_instance_profile(role_name):
    resource = {
        f'{role_name}_instance_profile': {
            "name": role_name,
            "role": build_role_name_ref(role_name)
        }
    }
    return resource


def batch_com_env(compute_environment_name, env_type, service_role, state,
                  res_type=None, minv_cpus=None, desired_vcpus=None,
                  maxv_cpus=None,
                  instance_types=None, security_group_ids=None, subnets=None,
                  instance_role=None):
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
    if instance_role:
        comp_resources['instance_role'] = build_role_arn_ref(
            role_name=instance_role)

    if comp_resources:
        params['compute_resources'] = comp_resources

    resource = {
        compute_environment_name: params
    }
    return resource
