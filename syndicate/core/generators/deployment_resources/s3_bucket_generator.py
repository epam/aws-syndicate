from syndicate.commons.log_helper import get_logger
from syndicate.core.generators.contents import S3_BUCKET_WEBSITE_HOSTING_POLICY
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
        },
        'tags': dict
    }

    def __init__(self, **kwargs):
        self.static_website_hosting = kwargs.get('static_website_hosting')
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        result = super()._generate_resource_configuration()
        if self.static_website_hosting:
            read_policy = S3_BUCKET_WEBSITE_HOSTING_POLICY
            read_policy['Statement'][0]['Resource'][0] = \
                read_policy['Statement'][0]['Resource'][0].format(
                    bucket_name=self.resource_name)
            if result['acl'].startswith('public'):
                read_policy['Statement'][0].pop('Condition')

            result['policy'] = read_policy
            result['website_hosting'] = {
                'enabled': True,
                'index_document': 'index.html',
                'error_document': 'error.html'
            }
            _LOG.info(f'Deployment resources of the S3 bucket '
                      f'\'{self.resource_name}\' modified for static website '
                      f'hosting.')
        return result
