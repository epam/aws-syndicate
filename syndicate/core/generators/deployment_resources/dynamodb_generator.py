import click
import json
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import DYNAMO_TABLE_TYPE
from syndicate.core.generators.deployment_resources.base_generator import \
    BaseDeploymentResourceGenerator, BaseConfigurationGenerator
from syndicate.core.generators import (_read_content_from_file,
                                       _write_content_to_file)

_LOG = get_logger(
    'syndicate.core.generators.deployment_resources.dynamodb_generator')
USER_LOG = get_user_logger()


class DynamoDBGenerator(BaseDeploymentResourceGenerator):
    RESOURCE_TYPE = DYNAMO_TABLE_TYPE
    CONFIGURATION = {
        'hash_key_name': None,
        'hash_key_type': None,
        'sort_key_name': None,
        'sort_key_type': None,
        'read_capacity': 1,
        'write_capacity': 1,
        'global_indexes': list,
        'autoscaling': list
    }


class DynamoDBGlobalIndexGenerator(BaseConfigurationGenerator):
    CONFIGURATION = {
        'name': None,
        'index_key_name': None,
        'index_key_type': None,
        'index_sort_key_name': None,
        'index_sort_key_type': None
    }

    def __init__(self, **kwargs):
        self.table_name = kwargs.pop('table_name')
        super().__init__(**kwargs)

    def write(self):
        """Adds global index to dynamodb"""
        paths_with_table = self._get_resource_meta_paths(self.table_name,
                                                         DYNAMO_TABLE_TYPE)
        if not paths_with_table:
            message = f"Table '{self.table_name}' was not found"
            _LOG.error(message)
            raise ValueError(message)
        path_with_table = paths_with_table[0]  # table can be declared once
        USER_LOG.info(f"Adding global index to table '{self.table_name}'...")
        deployment_resources = json.loads(_read_content_from_file(
            path_with_table
        ))
        deployment_resources[self.table_name]['global_indexes'].append(
            self._resolve_configuration()
        )
        _write_content_to_file(path_with_table,
                               json.dumps(deployment_resources, indent=2))


class DynamoDBAutoscalingGenerator(BaseConfigurationGenerator):
    CONFIGURATION = {
        'resource_name': None,
        'role_name': 'AWSServiceRoleForApplicationAutoScaling_DynamoDBTable',
        'min_capacity': 1,
        'max_capacity': 10,
        'config': {
            "policy_name": None,
            "target_utilization": 70,
            "scale_in_cooldown": 60,  # seconds
            "scale_out_cooldown": 60
        },
        'dimension': "dynamodb:table:ReadCapacityUnits",
    }

    def __init__(self, **kwargs):
        self.table_name = kwargs.pop('table_name')
        kwargs['resource_name'] = self.table_name
        super().__init__(**kwargs)

    def write(self):
        """Adds autoscaling to dynamodb"""
        paths_with_table = self._get_resource_meta_paths(self.table_name,
                                                         DYNAMO_TABLE_TYPE)
        if not paths_with_table:
            message = f"Table '{self.table_name}' was not found"
            _LOG.error(message)
            raise ValueError(message)
        path_with_table = paths_with_table[0]
        USER_LOG.info(f"Adding autoscaling to table '{self.table_name}'...")
        deployment_resources = json.loads(_read_content_from_file(
            path_with_table
        ))
        deployment_resources[self.table_name]['autoscaling'].append(
            self._resolve_configuration()
        )
        _write_content_to_file(path_with_table,
                               json.dumps(deployment_resources, indent=2))
