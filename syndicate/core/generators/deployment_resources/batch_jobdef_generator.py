from syndicate.core.constants import BATCH_JOBDEF_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator


class BatchJobdefGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = BATCH_JOBDEF_TYPE
    CONFIGURATION = {
        'job_definition_type': None,
        'container_properties': {
            'image': 'alpine',
            'vcpus': 1,
            'memory': 1024,
            'readonly_root_filesystem': True,
            'command': list,
            'job_role_arn': None
        },
        'node_properties': dict,
        'retry_strategy': dict
    }
