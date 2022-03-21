from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import S3_BUCKET_TYPE


class S3Generator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = S3_BUCKET_TYPE
    CONFIGURATION = {
        'acl': 'private',
        'location': None,
        'cors': list,
        'policy': dict,
        'public_access_block': {
            'block_public_acls': True,
            'ignore_public_acls': True,
            'block_public_policy': True,
            'restrict_public_buckets': True
        }
    }
