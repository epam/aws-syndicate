from syndicate.core.constants import DAX_CLUSTER_TYPE
from syndicate.core.generators.deployment_resources.base_generator import BaseDeploymentResourceGenerator


class DaxClusterGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DAX_CLUSTER_TYPE
    CONFIGURATION = {
        'node_type': None,
        'iam_role_name': None,
        'replication_factor': 3,
        'security_group_ids': list,
        'availability_zones': list,
        'cluster_endpoint_encryption_type': 'TLS',
        'parameter_group_name': None,
        'subnet_group_name': None,
        'subnet_ids': []
    }