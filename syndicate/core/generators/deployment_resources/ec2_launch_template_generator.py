import copy

from syndicate.commons.log_helper import get_logger
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import EC2_LAUNCH_TEMPLATE_TYPE


_LOG = get_logger('syndicate.core.generators.deployment_resources.'
                  'ec2_launch_template_generator')


class EC2LaunchTemplateGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = EC2_LAUNCH_TEMPLATE_TYPE
    CONFIGURATION = {
        'version_description': None,
        'launch_template_data': dict
    }

    KEY_MAPPING = {
        'security_group_names': 'security_groups',
        'imds_version': 'imds_support'
    }

    NON_LT_DATA_KEYS = ['version_description']

    def write(self):
        lt_data = dict()
        _dict = copy.deepcopy(self._dict)
        _LOG.debug('Going to resolve launch template data')
        for key in self._dict:
            if key in self.NON_LT_DATA_KEYS:
                continue
            if key in self.KEY_MAPPING:
                if self._dict.get(key):
                    lt_data[self.KEY_MAPPING[key]] = _dict.pop(key)
            else:
                if self._dict.get(key):
                    lt_data[key] = _dict.pop(key)
        _dict['launch_template_data'] = lt_data
        _LOG.debug(f'Launch template parameters {_dict}')
        self._dict = _dict
        super().write()
