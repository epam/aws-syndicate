from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import S3_BUCKET_TYPE


class S3Generator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = S3_BUCKET_TYPE
    CONFIGURATION = {
        'acl': 'private',
        'location': None,
        'cors': list,
        'policy': dict
    }