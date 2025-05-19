import functools
import json
import os

import yaml
from functools import reduce
from typing import Union, Any, Optional

from commons.constants import UPDATE_COMMAND


def save_json(output_file, data):
    with open(output_file, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def find_max_lambda_layer_version(layer_versions: list[dict]):
    if not layer_versions:
        return None

    max_version_dict = layer_versions[0]

    for layer in layer_versions:
        if layer['Version'] > max_version_dict['Version']:
            max_version_dict = layer

    return max_version_dict


def full_path(value: str, working_dir: str = None) -> str:
    if not value.endswith('.json'):
        value = value + '.json'
    if not os.path.isabs(value):  # check if full path
        if working_dir:
            value = os.path.join(working_dir, value)
        else:
            value = os.path.join(os.getcwd(), value)
    return value


def deep_get(dct: dict, path: Union[list, tuple], default=None) -> Any:
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        path, dct)


def populate_resources_prefix_suffix(resources: dict,
                                     prefix: Optional[str] = None,
                                     suffix: Optional[str] = None) -> dict:
    final_resources = {}
    for res_name, res_meta in resources.items():
        if prefix:
            res_name = prefix + res_name
        if suffix:
            res_name = res_name + suffix
        final_resources[res_name] = res_meta
    return final_resources


def populate_prefix_suffix(resource: str,
                           prefix: Optional[str] = None,
                           suffix: Optional[str] = None) -> str:
    res_name = resource
    if prefix:
        res_name = prefix + res_name
    if suffix:
        res_name = res_name + suffix
    return res_name


def transform_tags(original_tags: list[dict]):
    """
    Transforms one tag dictionary to another
    {
    'Tags': [
        {
            'Key': 'string',
            'Value': 'string'
        },
        ]
    }

    ---->

    {'Tags': {'string': 'string'}}
    """
    transformed_tags = {}

    for tag in original_tags:
        key = tag.get('Key', '')
        value = tag.get('Value')
        transformed_tags[key] = value

    return transformed_tags


def compare_dicts(dict1: dict, dict2: dict) -> Optional[set]:
    """
    return None if equals, otherwise return missing elements from second dict
    """
    set1 = set(dict1.items())
    set2 = set(dict2.items())

    if set1 == set2:
        return
    return set2 - set1


class UpdateContent(object):

    def __init__(self, command: str,
                 lambda_paths: list[str],
                 appsync_path: list[str],
                 resources_paths: list[str] = None):
        """
        lambda_paths: where lambda config and lambda_updated config files are stored
        appsync_path: where appsync config and appsync_updated config files are stored
        resources_paths: where deployment_resources.json and deployment_resources_updated.json files are stored.
        Default path - project folder
        """
        project_path = read_syndicate().get('project_path')
        self.lambda_conf_paths = []
        self.deployment_resources_paths = []
        self.appsync_paths = []

        for path in lambda_paths:
            self.lambda_conf_paths.append(
                (os.path.join(project_path, path, 'lambda_config.json'),
                 os.path.join(project_path, path, 'lambda_config_updated.json'))
            )

        if resources_paths:
            for path in resources_paths:
                self.deployment_resources_paths.append(
                    (os.path.join(project_path, path,
                                  'deployment_resources.json'),
                     os.path.join(project_path, path,
                                  'deployment_resources_updated.json')))
        else:
            self.deployment_resources_paths.append(
                (os.path.join(project_path, 'deployment_resources.json'),
                 os.path.join(project_path,
                              'deployment_resources_updated.json')))

        for path in appsync_path:
            self.appsync_paths.append(
                (os.path.join(project_path, path, 'appsync_config.json'),
                 os.path.join(project_path, path, 'appsync_config_updated.json'))
            )

        self.command = command
        self.lambda_initial_content = {}
        self.resources_initial_content = {}
        self.appsync_initial_content = {}

    def __enter__(self):
        if UPDATE_COMMAND in self.command:
            for path, updated_path in self.lambda_conf_paths:
                if not os.path.exists(path):
                    print(f'Invalid path {path}. Cannot update this file')
                    continue
                if not os.path.exists(updated_path):
                    print(f'Invalid path {updated_path}. '
                          f'Cannot update this file')
                    continue

                self.lambda_initial_content[path] = json.load(open(path, 'r'))
                updated_lambda_content = json.load(open(updated_path, 'r'))
                json.dump(updated_lambda_content, open(path, 'w'), indent=2)

            for path, updated_path in self.deployment_resources_paths:
                if not os.path.exists(path):
                    print(f'Invalid path {path}. Cannot update this file')
                    continue
                if not os.path.exists(updated_path):
                    print(f'Invalid path {updated_path}. '
                          f'Cannot update this file')
                    continue

                self.resources_initial_content[path] = json.load(
                    open(path, 'r')
                )
                updated_deployment_content = json.load(open(updated_path, 'r'))
                json.dump(updated_deployment_content, open(path, 'w'), indent=2)

            for path, updated_path in self.appsync_paths:
                if not os.path.exists(path):
                    print(f'Invalid path {path}. Cannot update this file')
                    continue
                if not os.path.exists(updated_path):
                    print(f'Invalid path {updated_path}. '
                          f'Cannot update this file')
                    continue

                self.appsync_initial_content[path] = json.load(
                    open(path, 'r')
                )
                updated_appsync_content = json.load(open(updated_path, 'r'))
                json.dump(updated_appsync_content, open(path, 'w'), indent=2)

    def __exit__(self, type, value, traceback):
        if UPDATE_COMMAND in self.command:
            for path, content in self.lambda_initial_content.items():
                json.dump(content, open(path, 'w'), indent=2)

            for path, content in self.resources_initial_content.items():
                json.dump(content, open(path, 'w'), indent=2)

            for path, content in self.appsync_initial_content.items():
                json.dump(content, open(path, 'w'), indent=2)


def split_deploy_bucket_path(deploy_target_bucket: str) -> tuple[str, list]:
    if deploy_target_bucket.startswith('/'):
        deploy_target_bucket = '/'.join(deploy_target_bucket.split('/')[1:])

    if '/' in deploy_target_bucket:
        bucket = deploy_target_bucket.split('/')[0]
        return bucket, deploy_target_bucket.split('/')[1:]
    return deploy_target_bucket, []


@functools.cache
def read_syndicate_aliases() -> Optional[dict]:
    conf_path = os.environ.get('SDCT_CONF')
    if not conf_path:
        return

    aliases_conf_file_path = os.path.join(conf_path, 'syndicate_aliases.yml')
    with open(aliases_conf_file_path, 'r') as file:
        try:
            content = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(f'Cannot parse {aliases_conf_file_path}: {exc}')
            return

    return content


def read_syndicate() -> Optional[dict]:
    conf_path = os.environ.get('SDCT_CONF')
    if not conf_path:
        return

    syndicate_conf_file_path = os.path.join(conf_path, 'syndicate.yml')
    with open(syndicate_conf_file_path, 'r') as file:
        try:
            content = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(f'Cannot parse {syndicate_conf_file_path}: {exc}')
            return

    return content
