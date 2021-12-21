from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.constants import BATCH_JOBQUEUE_TYPE
from syndicate.core.resources.batch_jobqueue_resource import DEFAULT_STATE


class BatchJobqueueGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = BATCH_JOBQUEUE_TYPE
    CONFIGURATION = {
        "state": DEFAULT_STATE,
        "priority": 1,
        "compute_environment_order": list,
    }

    def __init__(self, **kwargs):
        self.compute_environment_order = \
            kwargs.pop('compute_environment_order') or []
        super().__init__(**kwargs)

    def _generate_resource_configuration(self) -> dict:
        result = super()._generate_resource_configuration()
        for order, compute_env in self.compute_environment_order:
            result['compute_environment_order'].append(
                {'order': order, 'compute_environment': compute_env})
        return result
