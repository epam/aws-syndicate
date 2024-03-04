from syndicate.commons.log_helper import get_logger
from syndicate.core.generators.contents import S3_BUCKET_PUBLIC_READ_POLICY
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import S3_BUCKET_TYPE

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.base_generator')


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

    def __init__(self, **kwargs):
        self.static_website_hosting = kwargs.get('static_website_hosting')
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        result = super()._generate_resource_configuration()
        if self.static_website_hosting:
            result['policy'] = S3_BUCKET_PUBLIC_READ_POLICY
            result['acl'] = 'public-read'
            result['public_access_block'] = {
                'block_public_acls': False,
                'ignore_public_acls': False,
                'block_public_policy': False,
                'restrict_public_buckets': False
            }
            result['website_hosting'] = {
                'enabled': True,
                'index_document': 'index.html',
                'error_document': 'error.html'
            }
            _LOG.info(f'Deployment resources of the S3 bucket '
                      f'\'{self.resource_name}\' modified for static website '
                      f'hosting.')
        return result
