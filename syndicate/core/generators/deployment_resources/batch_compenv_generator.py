from syndicate.core.constants import BATCH_COMPENV_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator


class BatchCompenvGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = BATCH_COMPENV_TYPE
    CONFIGURATION = {
        "compute_environment_type": "MANAGED",
        "state": "ENABLED",
        "service_role": None,
        "compute_resources": {  # the ones from boto3 just in snake case
            "type": "EC2",
            "allocation_strategy": None,
            "minv_cpus": 0,
            "maxv_cpus": 8,
            "desiredv_cpus": 1,
            "instance_types": list,
            "security_group_ids": list,
            "subnets": list,
            "instance_role": None,
        }
    }

    def __init__(self, **kwargs):
        if kwargs.get('type') != 'FARGATE' and not kwargs['instance_types']:
            kwargs['instance_types'] = ['optimal']
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        result = super()._generate_resource_configuration()
        if result['compute_resources']['type'] in ['FARGATE', 'FARGATE_SPOT']:
            result['compute_resources'].pop('desiredv_cpus')
            result['compute_resources'].pop('minv_cpus')
            # Should I remove 'instance_role' here? because docs and
            # 'validate_batch_compenv' urges me, but aws api thinks differently
        return result
