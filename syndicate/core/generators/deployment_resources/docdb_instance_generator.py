import click
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import DOCUMENTDB_INSTANCE_TYPE, \
    DOCUMENTDB_CLUSTER_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.docdb_instance_generator')
USER_LOG = get_user_logger()


class DocumentDBInstanceGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DOCUMENTDB_INSTANCE_TYPE
    CONFIGURATION = {
        "cluster_identifier": None,
        "instance_class": "db.r5.large",
        "availability_zone": None
    }

    def write(self):
        cluster_identifier = self._dict.get('cluster_identifier')
        paths_with_cluster = self._get_resource_meta_paths(
            cluster_identifier,
            DOCUMENTDB_CLUSTER_TYPE)
        if not paths_with_cluster:
            message = f"Cluster '{cluster_identifier}' hasn't been declared " \
                      f"in deployment resources yet."
            _LOG.warn(message)
            if click.confirm(f"{message} Write DocumentDB instance anyway?"):
                USER_LOG.warn(f"Writing instance '{self.resource_name}' "
                              f"despite not declared cluster "
                              f"'{cluster_identifier}'")
            else:
                USER_LOG.warn(f"Skipping instance '{self.resource_name}'...")
                raise RuntimeError
        super().write()
