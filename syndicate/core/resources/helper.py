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

from syndicate.commons.log_helper import get_logger
from syndicate.core.conf.processor import GLOBAL_AWS_SERVICES

_LOG = get_logger('syndicate.core.resources.helper')


def validate_params(name, meta, required_params):
    existing_parameters = list(meta.keys())
    parameters_string = ', '.join(required_params)
    existing_parameters_string = ', '.join(existing_parameters)
    for each in required_params:
        if each not in existing_parameters:
            raise AssertionError(
                'All required parameters must be specified! Resource: {0}'
                ' Required parameters: {1}. Given parameters: {2}'.format(
                    name, parameters_string, existing_parameters_string))


def check_region_available(region_name, available_regions, res_meta=None):
    if region_name in available_regions:
        return True
    if res_meta:
        res_type = res_meta['resource_type']
        raise AssertionError(
            "Region {0} isn't available for resource {1}.".format(region_name,
                                                                  res_type))
    else:
        raise AssertionError("Region {0} isn't available.".format(region_name))


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
            raise AssertionError(
                'Invalid value region: {0}. Resource: {1}.'.format(region,
                                                                   name))
    return new_region_args


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def resolve_dynamic_identifier(name, value, dict):
    return json.loads(json.dumps(dict).replace(name, value))


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
        raise AssertionError(f'Missing required parameters: {missing}')
