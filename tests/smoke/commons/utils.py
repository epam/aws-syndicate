import json
import os
from functools import reduce
from typing import Union, Any


def save_json(output_file, data):
    with open(output_file, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def find_max_version(layer_versions):
    if not layer_versions:
        return None

    max_version_dict = layer_versions[0]

    for layer in layer_versions:
        if layer['Version'] > max_version_dict['Version']:
            max_version_dict = layer

    return max_version_dict


def full_path(value: str) -> str:
    if not value.endswith('.json'):
        value = value + '.json'
    if not os.path.isabs(value):  # check if full path
        value = os.path.join(os.getcwd(), value)
    return value


def deep_get(dct: dict, path: Union[list, tuple], default=None) -> Any:
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        path, dct)
