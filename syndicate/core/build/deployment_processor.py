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
from datetime import date, datetime

import concurrent
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor

from syndicate.commons.log_helper import get_logger
from syndicate.core.build.bundle_processor import (create_deploy_output,
                                                   load_deploy_output,
                                                   load_failed_deploy_output,
                                                   load_meta_resources,
                                                   remove_deploy_output,
                                                   remove_failed_deploy_output)
from syndicate.core.build.meta_processor import resolve_meta
from syndicate.core.constants import (BUILD_META_FILE_NAME,
                                      CLEAN_RESOURCE_TYPE_PRIORITY,
                                      DEPLOY_RESOURCE_TYPE_PRIORITY,
                                      LAMBDA_TYPE)
from syndicate.core.helper import exit_on_exception, prettify_json
from syndicate.core.resources import (APPLY_MAPPING, CREATE_RESOURCE,
                                      DESCRIBE_RESOURCE, REMOVE_RESOURCE,
                                      RESOURCE_CONFIGURATION_PROCESSORS,
                                      RESOURCE_IDENTIFIER, UPDATE_RESOURCE)

_LOG = get_logger('syndicate.core.build.deployment_processor')


def get_dependencies(name, meta, resources_dict, resources):
    """ Get dependencies from resources that needed to create them too.

    :type name: str
    :type meta: dict
    :type resources_dict: dict
    :param resources:
    :param resources_dict: resources that will be created {name: meta}
    """
    resources_dict[name] = meta
    if meta.get('dependencies'):
        for dependency in meta.get('dependencies'):
            dep_name = dependency['resource_name']
            dep_meta = resources[dep_name]
            resources_dict[dep_name] = dep_meta
            if dep_meta.get('dependencies'):
                get_dependencies(dep_name, dep_meta, resources_dict, resources)


# todo implement resources sorter according to priority
def _process_resources(resources, handlers_mapping):
    res_type = None
    output = {}
    args = []
    resource_type = None
    try:
        for res_name, res_meta in resources:
            res_type = res_meta['resource_type']

            if resource_type is None:
                resource_type = res_type

            if res_type == resource_type:
                args.append({'name': res_name, 'meta': res_meta})
                continue
            elif res_type != resource_type:
                _LOG.info('Processing {0} resources ...'.format(resource_type))
                func = handlers_mapping[resource_type]
                response = func(args)  # todo exception may be raised here
                if response:
                    output.update(response)
                del args[:]
                args.append({'name': res_name, 'meta': res_meta})
                resource_type = res_type
        if args:
            _LOG.info('Processing {0} resources ...'.format(resource_type))
            func = handlers_mapping[resource_type]
            response = func(args)
            if response:
                output.update(response)
        return True, output
    except Exception as e:
        _LOG.error('Error occurred while {0} resource creating: {1}'.format(
            res_type, e.message))
        # args list always contains one item here
        return False, update_failed_output(args[0]['name'], args[0]['meta'],
                                           resource_type, output)


def update_failed_output(res_name, res_meta, resource_type, output):
    describe_func = DESCRIBE_RESOURCE[resource_type]
    failed_resource_output = describe_func(res_name, res_meta)
    if failed_resource_output:
        if isinstance(failed_resource_output, list):
            for item in failed_resource_output:
                output.update(item)
        else:
            output.update(failed_resource_output)
    return output


def deploy_resources(resources):
    return _process_resources(resources=resources,
                              handlers_mapping=CREATE_RESOURCE)


def update_resources(resources):
    return _process_resources(resources=resources,
                              handlers_mapping=UPDATE_RESOURCE)


def clean_resources(output):
    args = []
    resource_type = None
    # clean all resources
    for arn, config in output:
        res_type = config['resource_meta']['resource_type']
        if resource_type is None:
            resource_type = res_type

        if res_type == resource_type:
            args.append({'arn': arn, 'config': config})
            continue
        elif res_type != resource_type:
            _LOG.info('Removing {0} resources ...'.format(resource_type))
            func = REMOVE_RESOURCE[resource_type]
            func(args)
            del args[:]
            args.append({'arn': arn, 'config': config})
            resource_type = res_type
    if args:
        _LOG.info('Removing {0} resources ...'.format(resource_type))
        func = REMOVE_RESOURCE[resource_type]
        func(args)


# todo implement saving failed output
def continue_deploy_resources(resources, failed_output):
    updated_output = {}
    deploy_result = True
    res_type = None
    try:
        args = []
        resource_type = None
        for res_name, res_meta in resources:
            res_type = res_meta['resource_type']

            if resource_type is None:
                resource_type = res_type

            if res_type == resource_type:
                resource_output = __find_output_by_resource_name(
                    failed_output, res_name)
                args.append(
                    {
                        'name': res_name,
                        'meta': res_meta,
                        'current_configurations': resource_output
                    })
                continue
            elif res_type != resource_type:
                func = RESOURCE_CONFIGURATION_PROCESSORS.get(resource_type)
                if func:
                    response = func(args)
                    if response:
                        updated_output.update(
                            json.loads(
                                json.dumps(response, default=_json_serial)))
                else:
                    # function to update resource is not present
                    # move existing output for resources to new output
                    __move_output_content(args, failed_output, updated_output)
                del args[:]
                resource_output = __find_output_by_resource_name(
                    failed_output, res_name)
                args.append({
                    'name': res_name,
                    'meta': res_meta,
                    'current_configurations': resource_output
                })
                resource_type = res_type
        if args:
            func = RESOURCE_CONFIGURATION_PROCESSORS.get(resource_type)
            if func:
                response = func(args)
                if response:
                    updated_output.update(
                        json.loads(
                            json.dumps(response, default=_json_serial)))
            else:
                # function to update resource is not present
                # move existing output- for resources to new output
                __move_output_content(args, failed_output, updated_output)
    except Exception as e:
        _LOG.error('Error occurred while {0} resource creating: {1}'.format(
            res_type, e.message))
        deploy_result = False

    return deploy_result, updated_output


def __move_output_content(args, failed_output, updated_output):
    for arg in args:
        resource_output = __find_output_by_resource_name(
            failed_output, arg['name'])
        if resource_output:
            updated_output.update(resource_output)


def __find_output_by_resource_name(output, resource_name):
    found_items = {}
    for k, v in output.iteritems():
        if v['resource_name'] == resource_name:
            found_items[k] = v
    return found_items


def create_deployment_resources(deploy_name, bundle_name,
                                deploy_only_resources=None,
                                deploy_only_types=None,
                                excluded_resources=None, excluded_types=None):
    resources = resolve_meta(load_meta_resources(bundle_name))
    _LOG.debug('Names were resolved')
    _LOG.debug(prettify_json(resources))

    # validate_deployment_packages(resources)
    _LOG.info('{0} file was loaded successfully'.format(BUILD_META_FILE_NAME))

    # TODO make filter chain
    if deploy_only_resources:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k in deploy_only_resources)

    if excluded_resources:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k not in excluded_resources)
    if deploy_only_types:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         v['resource_type'] in deploy_only_types)

    if excluded_types:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         v['resource_type'] not in excluded_types)

    _LOG.debug('Going to create: {0}'.format(prettify_json(resources)))

    # sort resources with priority
    resources_list = resources.items()
    resources_list.sort(cmp=_compare_deploy_resources)

    _LOG.info('Going to deploy AWS resources')
    success, output = deploy_resources(resources_list)
    if success:
        _LOG.info('AWS resources were deployed successfully')

        # apply dynamic changes that uses ARNs
        _LOG.info('Going to apply dynamic changes')
        _apply_dynamic_changes(resources, output)
        _LOG.info('Dynamic changes were applied successfully')

    _LOG.info('Going to create deploy output')
    output_str = json.dumps(output, default=_json_serial)
    create_deploy_output(bundle_name, deploy_name, output_str, success)
    _LOG.info('Deploy output for {0} was created.'.format(deploy_name))
    return success


@exit_on_exception
def remove_deployment_resources(deploy_name, bundle_name,
                                clean_only_resources=None,
                                clean_only_types=None,
                                excluded_resources=None, excluded_types=None):
    output = load_deploy_output(bundle_name, deploy_name)
    _LOG.info('Output file was loaded successfully')

    # TODO make filter chain
    if clean_only_resources:
        output = dict((k, v) for (k, v) in output.iteritems() if
                      v['resource_name'] in clean_only_resources)

    if excluded_resources:
        output = dict((k, v) for (k, v) in output.iteritems() if
                      v['resource_name'] not in excluded_resources)

    if clean_only_types:
        output = dict((k, v) for (k, v) in output.iteritems() if
                      v['resource_meta']['resource_type'] in clean_only_types)

    if excluded_types:
        output = dict((k, v) for (k, v) in output.iteritems() if
                      v['resource_meta'][
                          'resource_type'] not in excluded_types)

    # sort resources with priority
    resources_list = output.items()
    resources_list.sort(cmp=_compare_clean_resources)
    _LOG.debug('Resources to delete: {0}'.format(resources_list))

    _LOG.info('Going to clean AWS resources')
    clean_resources(resources_list)
    # remove output from bucket
    remove_deploy_output(bundle_name, deploy_name)


@exit_on_exception
def continue_deployment_resources(deploy_name, bundle_name,
                                  deploy_only_resources=None,
                                  deploy_only_types=None,
                                  excluded_resources=None,
                                  excluded_types=None):
    output = load_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Failed output file was loaded successfully')

    resources = resolve_meta(load_meta_resources(bundle_name))
    _LOG.debug('Names were resolved')
    _LOG.debug(prettify_json(resources))

    # TODO make filter chain
    if deploy_only_resources:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k in deploy_only_resources)

    if excluded_resources:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k not in excluded_resources)
    if deploy_only_types:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         v['resource_type'] in deploy_only_types)

    if excluded_types:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         v['resource_type'] not in excluded_types)

    # sort resources with priority
    resources_list = resources.items()
    resources_list.sort(cmp=_compare_deploy_resources)

    success, updated_output = continue_deploy_resources(resources_list, output)
    _LOG.info('AWS resources were deployed successfully')
    if success:
        # apply dynamic changes that uses ARNs
        _LOG.info('Going to apply dynamic changes')
        _apply_dynamic_changes(resources, updated_output)
        _LOG.info('Dynamic changes were applied successfully')

    # remove failed output from bucket
    remove_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Going to create deploy output')
    create_deploy_output(bundle_name, deploy_name,
                         prettify_json(updated_output), success=success)
    return success


@exit_on_exception
def remove_failed_deploy_resources(deploy_name, bundle_name):
    output = load_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Failed output file was loaded successfully')
    # sort resources with priority
    resources_list = output.items()
    resources_list.sort(cmp=_compare_clean_resources)

    _LOG.info('Going to clean AWS resources')
    clean_resources(resources_list)
    # remove output from bucket
    remove_failed_deploy_output(bundle_name, deploy_name)


@exit_on_exception
def update_lambdas(bundle_name,
                   publish_only_lambdas,
                   excluded_lambdas_resources):
    resources = resolve_meta(load_meta_resources(bundle_name))
    _LOG.debug('Names were resolved')
    _LOG.debug(prettify_json(resources))

    # TODO make filter chain
    resources = dict((k, v) for (k, v) in resources.iteritems() if
                     v['resource_type'] == LAMBDA_TYPE)

    if publish_only_lambdas:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k in publish_only_lambdas)

    if excluded_lambdas_resources:
        resources = dict((k, v) for (k, v) in resources.iteritems() if
                         k not in excluded_lambdas_resources)

    _LOG.debug('Going to update the following lambdas: {0}'.format(
        prettify_json(resources)))
    resources = resources.items()
    update_resources(resources=resources)


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def _apply_dynamic_changes(resources, output):
    pool = ThreadPoolExecutor(max_workers=5)
    futures = []
    for name, meta in resources.iteritems():
        resource_type = meta['resource_type']
        apply_changes = meta.get('apply_changes')
        if apply_changes:
            for apply_item in apply_changes:
                change_type = apply_item['apply_type']
                dependency_name = apply_item['dependency_name']
                res_config = resources.get(dependency_name)
                if not res_config:
                    _LOG.debug('Dependency resource {0} is not found, '
                               'skipping the apply'.format(dependency_name))
                else:
                    dependency_type = res_config['resource_type']
                    func = RESOURCE_IDENTIFIER.get(resource_type)
                    if func:
                        resource_output = __find_output_by_resource_name(
                            output, name)
                        identifier = func(name, resource_output)
                        apply_func = APPLY_MAPPING.get(change_type)
                        if apply_func:
                            alias = '#{' + name + '}'
                            f = pool.submit(apply_func, alias, identifier,
                                            apply_item)
                            futures.append(f)
                        else:
                            _LOG.warn('Dynamic apply is not defined '
                                      'for {0} type'.format(change_type))
                    else:
                        _LOG.warn('Resource identifier is not defined '
                                  'for {0} type'.format(dependency_type))
            _LOG.info('Dynamic changes were applied to {0}'.format(name))
    concurrent.futures.wait(futures, timeout=None, return_when=ALL_COMPLETED)


def _compare_deploy_resources(first, second):
    first_resource_type = first[-1]['resource_type']
    second_resource_type = second[-1]['resource_type']
    first_res_priority = DEPLOY_RESOURCE_TYPE_PRIORITY[first_resource_type]
    second_res_priority = DEPLOY_RESOURCE_TYPE_PRIORITY[second_resource_type]
    return _compare_res(first_res_priority, second_res_priority)


def _compare_clean_resources(first, second):
    first_resource_type = first[-1]['resource_meta']['resource_type']
    second_resource_type = second[-1]['resource_meta']['resource_type']
    first_res_priority = CLEAN_RESOURCE_TYPE_PRIORITY[first_resource_type]
    second_res_priority = CLEAN_RESOURCE_TYPE_PRIORITY[second_resource_type]
    return _compare_res(first_res_priority, second_res_priority)


def _compare_res(first_res_priority, second_res_priority):
    if first_res_priority < second_res_priority:
        return -1
    elif first_res_priority > second_res_priority:
        return 1
    else:
        return 0
