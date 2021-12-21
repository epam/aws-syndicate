import click
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import BATCH_JOBQUEUE_TYPE, BATCH_COMPENV_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator
from syndicate.core.resources.batch_jobqueue_resource import DEFAULT_STATE

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.batch_jobqueue')
USER_LOG = get_user_logger()


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
            paths_with_compute_env = self._get_resource_meta_paths(
                compute_env, BATCH_COMPENV_TYPE
            )
            if not paths_with_compute_env:
                message = f"Compute env '{compute_env}' hasn't been declared " \
                          f"in deployment resources yet."
                _LOG.warn(message)
                if click.confirm(
                        f"{message} Write compute env order anyway?"):
                    USER_LOG.warn(f"Writing compute env order "
                                  f"despite not declared compute env "
                                  f"'{compute_env}'")
                else:
                    USER_LOG.warn(
                        f"Skipping compute env in order '{compute_env}'...")
                    continue
            result['compute_environment_order'].append(
                {'order': order, 'compute_environment': compute_env})
        return result
