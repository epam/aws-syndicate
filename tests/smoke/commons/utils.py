import json
import os
from functools import reduce
from typing import Union, Any, Optional


def save_json(output_file, data):
    with open(output_file, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def find_max_lambda_layer_version(layer_versions):
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


def populate_prefix_suffix(resources: dict, prefix: Optional[str] = None,
                           suffix: Optional[str] = None) -> dict:
    final_resources = {}
    for res_name, res_meta in resources.items():
        if prefix:
            res_name = prefix + res_name
        if suffix:
            res_name = res_name + suffix
        final_resources[res_name] = res_meta
    return final_resources
