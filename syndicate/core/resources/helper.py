"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import json
import re

from syndicate.exceptions import ParameterError, ResourceProcessingError, InvalidValueError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.conf.processor import GLOBAL_AWS_SERVICES
from typing import TypeVar, Optional, Iterable
from datetime import datetime

T = TypeVar('T')

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def validate_params(name, meta, required_params):
    existing_parameters = list(meta.keys())
    parameters_string = ', '.join(required_params)
    existing_parameters_string = ', '.join(existing_parameters)
    for each in required_params:
        if each not in existing_parameters:
            raise ParameterError(
                f"All required parameters must be specified! "
                f"Resource: '{name}' "
                f"Required parameters: '{parameters_string}'. "
                f"Given parameters: '{existing_parameters_string}'"
            )


def validate_known_params(name: str, act_params: Iterable,
                          known_params: Iterable):
    unknown_params = []
    for param in act_params:
        if param not in known_params:
            unknown_params.append(param)

    if unknown_params:
        raise ParameterError(
            f"Unknown parameter/s detected in the '{name}' configuration. "
            f"Unknown parameter/s: {unknown_params}. "
            f"Must be one of: {known_params}"
        )


def validate_date(name, date_str):
    """
    Checks if the provided date in `date_str` is in ISO 8601 or Unix timestamp format
    """
    try:
        datetime.fromisoformat(date_str)
        unix_timestamp = int(date_str)
        datetime.utcfromtimestamp(unix_timestamp)
        return date_str
    except Exception as e:
        raise InvalidValueError(
            f"Invalid date format: '{date_str}'. Resource: '{name}' "
            f"Error message: {e}"
        )


def check_region_available(region_name, available_regions, res_meta=None):
    if region_name in available_regions:
        return True
    if res_meta:
        res_type = res_meta['resource_type']
        raise ResourceProcessingError(
            f"Region '{region_name}' isn't available for resource '{res_type}'."
        )
    else:
        raise ResourceProcessingError(
            f"Region '{region_name}' isn't available."
        )


def create_args_for_multi_region(args, available_regions):
    from syndicate.core import CONFIG
    new_region_args = []
    for arg_set in args:
        name = arg_set['name']
        meta = arg_set['meta']
        region = meta.get('region')
        if region is None:
            item = arg_set.copy()
            item['region'] = CONFIG.region
            new_region_args.append(item)
        elif isinstance(region, str):
            if region == 'all':
                for each in available_regions:
                    item = arg_set.copy()
                    item['region'] = each
                    new_region_args.append(item)
            else:
                if check_region_available(region, available_regions, meta):
                    item = arg_set.copy()
                    item['region'] = region
                    new_region_args.append(item)
        elif isinstance(region, list):
            for each in region:
                if check_region_available(each, available_regions, meta):
                    item = arg_set.copy()
                    item['region'] = each
                    new_region_args.append(item)
        else:
            raise InvalidValueError(
                f"Invalid value region: '{region}'. Resource: '{name}'."
            )
    return new_region_args


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def resolve_dynamic_identifier(to_replace, resource_meta):
    """
    Replaces keys from 'to_replace' with values from it inside json built
    from 'resource_meta'
    :type to_replace: dict
    :type resource_meta: dict
    """
    raw_json = json.dumps(resource_meta)
    for name, value in to_replace.items():
        raw_json = raw_json.replace(name, value)
    return json.loads(raw_json)


def detect_unresolved_aliases(resource_meta: dict) -> None:
    """
    Extract unresolved aliases in the given meta string.
    :param resource_meta: Input dict.
    """
    pattern = r'\$\{([^}]+)\}'
    if missing_aliases := list(set(re.findall(pattern,
                                              json.dumps(resource_meta)))):
        placeholders = [f'${{{alias}}}' for alias in missing_aliases]
        USER_LOG.warning(
            'Unresolved alias placeholders are present in the meta, which may '
            'lead to errors in resource processing. Please check the '
            'syndicate aliases and resource definitions. '
            f'Unresolved placeholders: {placeholders}')


def build_description_obj(response, name, meta):
    resource_type = meta['resource_type']
    obj = {
        'resource_name': name,
        'resource_meta': meta,
        'description': response
    }
    if resource_type not in GLOBAL_AWS_SERVICES:
        from syndicate.core import CONFIG
        obj['resource_meta']['region'] = meta.get('region', CONFIG.region)
    return obj


def assert_required_params(required_params_names, all_params):
    """
    Raises error if there is at least one missing parameter.
    :param required_params_names:
    :param all_params:
    :return:
    """
    missing = [param for param in required_params_names if
               param not in all_params.keys()]
    if missing:
        raise ParameterError(f"Missing required parameters: '{missing}'")


def assert_possible_values(iterable: list, possible: list):
    if not set(iterable).issubset(set(possible)):
        message = f'Incorrect values in given iterable: {iterable}. ' \
                  f'Must be a subset of these: {possible}'
        _LOG.error(message)
        raise InvalidValueError(message)


def filter_dict_by_shape(d, shape):
    new_d = {}
    for attribute, value in shape.items():
        if value is None:
            new_d[attribute] = d.get(attribute)

        if isinstance(value, list):
            new_d[attribute] = filter_list_by_shape(d.get(attribute), value)

        if isinstance(value, dict):
            new_d[attribute] = filter_dict_by_shape(d.get(attribute), value)
    return new_d


def filter_list_by_shape(lst, shape):
    if not shape[0] or not lst:
        return lst

    new_lst = []
    if isinstance(shape[0], dict):
        for d in lst:
            new_lst.append(filter_dict_by_shape(d, shape[0]))

    return new_lst


def if_updated(new: T, old: T) -> Optional[T]:
    """
    If `new` differs from `old` it `new` will be returned.
    If it does not, None is returned. They must be comparable
    """
    return new if new != old else None
