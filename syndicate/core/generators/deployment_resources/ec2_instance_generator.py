from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import EC2_INSTANCE_TYPE


class EC2InstanceGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = EC2_INSTANCE_TYPE
    CONFIGURATION = {
        'key_name': None,
        'image_id': None,
        'instance_type': 't2.micro',
        'availability_zone': None,
        'subnet_id': None,
        'userdata_file': None,
        'disableApiTermination': True,
        'iam_role': None,
        'security_group_names': list,
        'security_group_ids': list,
    }

    def __init__(self, **kwargs):
        if 'disable_api_termination' in kwargs:
            kwargs['disableApiTermination'] = kwargs.pop(
                'disable_api_termination')
        super().__init__(**kwargs)
