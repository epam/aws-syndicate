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
import concurrent
import functools
import json
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor
from functools import cmp_to_key

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.bundle_processor import (create_deploy_output,
                                                   load_deploy_output,
                                                   load_failed_deploy_output,
                                                   load_meta_resources,
                                                   remove_deploy_output,
                                                   remove_failed_deploy_output,
                                                   load_latest_deploy_output)
from syndicate.core.build.helper import _json_serial
from syndicate.core.build.meta_processor import (resolve_meta,
                                                 populate_s3_paths,
                                                 resolve_resource_name)

from syndicate.core.constants import (BUILD_META_FILE_NAME,
                                      CLEAN_RESOURCE_TYPE_PRIORITY,
                                      DEPLOY_RESOURCE_TYPE_PRIORITY,
                                      UPDATE_RESOURCE_TYPE_PRIORITY,
                                      PARTIAL_CLEAN_ACTION)
from syndicate.core.helper import exit_on_exception, prettify_json


_LOG = get_logger('syndicate.core.build.deployment_processor')
USER_LOG = get_user_logger()


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
def _process_resources(resources, handlers_mapping, pass_context=False):
    output = {}
    args = []
    resource_type = None
    try:
        for res_name, res_meta in resources:
            current_res_type = res_meta['resource_type']

            if resource_type is None:
                resource_type = current_res_type

            if current_res_type == resource_type:
                args.append(_build_args(name=res_name,
                                        meta=res_meta,
                                        context=output,
                                        pass_context=pass_context))
                continue
            elif current_res_type != resource_type:
                USER_LOG.info(f'Processing {resource_type} resources')
                func = handlers_mapping[resource_type]
                response = func(args)  # todo exception may be raised here
                if response:
                    output.update(response)
                del args[:]
                args.append(_build_args(name=res_name,
                                        meta=res_meta,
                                        context=output,
                                        pass_context=pass_context))
                resource_type = current_res_type
        if args:
            USER_LOG.info(f'Processing {resource_type} resources')
            func = handlers_mapping[resource_type]
            response = func(args)
            if response:
                output.update(response)
        return True, output
    except Exception as e:
        USER_LOG.exception('Error occurred while {0} '
                           'resource creating: {1}'.format(resource_type,
                                                           str(e)))
        # args list always contains one item here
        return False, update_failed_output(args[0]['name'], args[0]['meta'],
                                           resource_type, output)


def _build_args(name, meta, context, pass_context=False):
    """
    Builds parameters to pass to resource_type handler.
    Default parameters dict consists of name and meta keys.
    If pass_context set to True, parameters dict is extended with 'context' key
    :param name: name of the resource
    :param meta: definition of the resource
    :param context: result of previously deployed resources in scope of current syndicate execution
    :param pass_context: flag. Manages if output will be included to parameters
    :return: prepared parameters to be passed to resource_type handler.
    """
    params = {'name': name, 'meta': meta}
    if pass_context:
        params['context'] = context
    return params


def update_failed_output(res_name, res_meta, resource_type, output):
    from syndicate.core import PROCESSOR_FACADE

    try:
        describe_func = PROCESSOR_FACADE.describe_handlers()[resource_type]
        failed_resource_output = describe_func(res_name, res_meta)
        if failed_resource_output:
            if isinstance(failed_resource_output, list):
                for item in failed_resource_output:
                    output.update(item)
            else:
                output.update(failed_resource_output)
    except Exception as e:
        _LOG.warning(f'Unable to describe {resource_type} '
                     f'resource with name {res_name}. Exception: {e}')
    return output


def deploy_resources(resources):
    from syndicate.core import PROCESSOR_FACADE
    return _process_resources(
        resources=resources,
        handlers_mapping=PROCESSOR_FACADE.create_handlers())


def update_resources(resources):
    from syndicate.core import PROCESSOR_FACADE
    return _process_resources(
        resources=resources,
        handlers_mapping=PROCESSOR_FACADE.update_handlers(),
        pass_context=True)


def clean_resources(output):
    from syndicate.core import PROCESSOR_FACADE
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
            USER_LOG.info('Removing {0} resources ...'.format(resource_type))
            func = PROCESSOR_FACADE.remove_handlers()[resource_type]
            func(args)
            del args[:]
            args.append({'arn': arn, 'config': config})
            resource_type = res_type
    if args:
        USER_LOG.info('Removing {0} resources ...'.format(resource_type))
        func = PROCESSOR_FACADE.remove_handlers()[resource_type]
        func(args)


# todo implement saving failed output
def continue_deploy_resources(resources, failed_output):
    from syndicate.core import PROCESSOR_FACADE
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
                func = PROCESSOR_FACADE.resource_configuration_processor() \
                    .get(resource_type)
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
            func = PROCESSOR_FACADE.resource_configuration_processor() \
                .get(resource_type)
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
        _LOG.exception(
            'Error occurred while {0} resource creating: {1}'.format(
                res_type, str(e)))
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
    for k, v in output.items():
        if v['resource_name'] == resource_name:
            found_items[k] = v
    return found_items


def _compare_external_resources(expected_resources):
    from syndicate.core import PROCESSOR_FACADE
    compare_funcs = PROCESSOR_FACADE.compare_meta_handlers()

    errors = {}

    for resource_name, resource_meta in expected_resources.items():
        func = compare_funcs[resource_meta.get('resource_type')]
        resource_errors = func(resource_name, resource_meta)
        if resource_errors:
            errors[resource_name] = resource_errors

    if errors:
        import os
        error = f'{os.linesep}'.join(errors.values())
        raise AssertionError(error)


@exit_on_exception
def create_deployment_resources(deploy_name, bundle_name,
                                deploy_only_resources=None,
                                deploy_only_types=None,
                                excluded_resources=None,
                                excluded_types=None,
                                replace_output=False):
    latest_deploy_output = load_latest_deploy_output()
    _LOG.debug(f'Latest deploy output:\n {latest_deploy_output}')

    resources = load_meta_resources(bundle_name)
    # validate_deployment_packages(resources)
    _LOG.debug('{0} file was loaded successfully'.format(BUILD_META_FILE_NAME))

    resources = resolve_meta(resources)
    _LOG.debug('Names were resolved')
    resources = populate_s3_paths(resources, bundle_name)
    _LOG.debug('Artifacts s3 paths were resolved')

    deploy_only_resources = _resolve_names(deploy_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    # TODO make filter chain
    if deploy_only_resources:
        resources = dict((k, v) for (k, v) in resources.items() if
                         k in deploy_only_resources)

    if excluded_resources:
        resources = dict((k, v) for (k, v) in resources.items() if
                         k not in excluded_resources)
    if deploy_only_types:
        resources = dict((k, v) for (k, v) in resources.items() if
                         v['resource_type'] in deploy_only_types)

    if excluded_types:
        resources = dict((k, v) for (k, v) in resources.items() if
                         v['resource_type'] not in excluded_types)

    _LOG.debug(prettify_json(resources))

    _LOG.debug('Going to create: {0}'.format(prettify_json(resources)))

    expected_external_resources = {key: value for key, value in
                                   resources.items() if value.get('external')}
    if expected_external_resources:
        _compare_external_resources(expected_external_resources)
        _LOG.info('External resources were matched successfully')

    # sort resources with priority
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(compare_deploy_resources))

    _LOG.info('Going to deploy AWS resources')
    success, output = deploy_resources(resources_list)
    if success:
        USER_LOG.info('AWS resources were deployed successfully')

        # apply dynamic changes that uses ARNs
        _LOG.info('Going to apply dynamic changes')
        _apply_dynamic_changes(resources, output)
        USER_LOG.info('Dynamic changes were applied successfully')

        _LOG.info('Going to apply common tags')
        _apply_tags(output)

    USER_LOG.info('Going to create deploy output')
    create_deploy_output(bundle_name=bundle_name,
                         deploy_name=deploy_name,
                         output={**output, **latest_deploy_output},
                         success=success,
                         replace_output=replace_output)
    USER_LOG.info('Deploy output for {0} was created.'.format(deploy_name))
    return success


@exit_on_exception
def update_deployment_resources(bundle_name, deploy_name, replace_output=False,
                                update_only_types=None,
                                update_only_resources=None):
    from syndicate.core import PROCESSOR_FACADE
    resources = load_meta_resources(bundle_name)
    _LOG.debug(prettify_json(resources))

    resources = resolve_meta(resources)
    _LOG.debug('Names were resolved')
    resources = populate_s3_paths(resources, bundle_name)
    _LOG.debug('Artifacts s3 paths were resolved')

    _LOG.warn(
        'Please pay attention that only the '
        'following resources types are supported for update: {}'.format(
            list(PROCESSOR_FACADE.update_handlers().keys())))

    update_only_resources = _resolve_names(update_only_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    # TODO make filter chain
    resources = dict((k, v) for (k, v) in resources.items() if
                     v['resource_type'] in
                     PROCESSOR_FACADE.update_handlers().keys())

    if update_only_types:
        resources = dict((k, v) for (k, v) in resources.items() if
                         v['resource_type'] in update_only_types)
    if update_only_resources:
        resources = dict((k, v) for (k, v) in resources.items() if
                         k in update_only_resources)

    _LOG.debug('Going to update the following resources: {0}'.format(
        prettify_json(resources)))
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(_compare_update_resources))
    success, output = _process_resources(
        resources=resources_list,
        handlers_mapping=PROCESSOR_FACADE.update_handlers(),
        pass_context=True)
    create_deploy_output(bundle_name=bundle_name,
                         deploy_name=deploy_name,
                         output=output,
                         success=success,
                         replace_output=replace_output)
    return success


def _cross_wired_filter(collection, control, target, dependencies,
                        chain: dict = None):
    chain = chain or {}
    for i, f in enumerate(control):
        s = i + len(dependencies)//2
        if any([dependencies[i], dependencies[s]]):
            temp, j, filter_collection = {}, (i + 1) % (len(dependencies)//2), \
                lambda func, c: dict(
                    filter(lambda item: func(item[1]), c.items())
                )
            temp = filter_collection(f, collection) \
                if dependencies[i] else collection
            temp = filter_collection(target[j], temp) \
                if dependencies[s] else temp
            temp = temp if dependencies[i] or not dependencies[j] else {}
            chain.update(temp)
    return chain


@exit_on_exception
def remove_deployment_resources(deploy_name, bundle_name,
                                clean_only_resources=None,
                                clean_only_types=None,
                                excluded_resources=None,
                                excluded_types=None,
                                clean_externals=None,
                                preserve_state=None):
    output = new_output = load_deploy_output(bundle_name, deploy_name)
    _LOG.info('Output file was loaded successfully')

    clean_only_resources = _resolve_names(clean_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    dependencies = tuple(map(bool, (clean_only_resources, clean_only_types,
                                    excluded_types, excluded_resources)))

    # todo refactor for more flexible approach
    if any(dependencies):
        filters = (
            lambda v: v.get('resource_name') in clean_only_resources,
            lambda v: v.get('resource_meta', {}).get('resource_type')
            in clean_only_types,
            lambda v: v.get('resource_name') not in excluded_resources,
            lambda v: v.get('resource_meta', {}).get('resource_type')
            not in excluded_types
        )
        if any(dependencies[:2]):
            new_output = _cross_wired_filter(new_output, filters[:2],
                                             filters[2:], dependencies)
        elif any(dependencies[2:]):
            for i, exclusion in enumerate(filters[2:]):
                new_output = _cross_wired_filter(new_output, [exclusion],
                                                 filters[i:i+1],
                                                 dependencies[::-1])
    if clean_externals:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          v['resource_meta'].get('external'))
    # sort resources with priority
    resources_list = list(new_output.items())
    resources_list.sort(key=cmp_to_key(_compare_clean_resources))
    _LOG.debug('Resources to delete: {0}'.format(resources_list))
    USER_LOG.info('Going to clean AWS resources')
    clean_resources(resources_list)
    # remove new_output from bucket
    return _post_remove_output_handling(
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        preserve_state=preserve_state,
        output=output,
        new_output=new_output,
        is_regular_output=True
    )


@exit_on_exception
def continue_deployment_resources(deploy_name, bundle_name,
                                  deploy_only_resources=None,
                                  deploy_only_types=None,
                                  excluded_resources=None,
                                  excluded_types=None,
                                  replace_output=False):
    output = load_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Failed output file was loaded successfully')

    resources = resolve_meta(load_meta_resources(bundle_name))
    _LOG.debug('Names were resolved')
    _LOG.debug(prettify_json(resources))

    deploy_only_resources = _resolve_names(deploy_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    # TODO make filter chain
    if deploy_only_resources:
        resources = dict((k, v) for (k, v) in resources.items() if
                         k in deploy_only_resources)

    if excluded_resources:
        resources = dict((k, v) for (k, v) in resources.items() if
                         k not in excluded_resources)
    if deploy_only_types:
        resources = dict((k, v) for (k, v) in resources.items() if
                         v['resource_type'] in deploy_only_types)

    if excluded_types:
        resources = dict((k, v) for (k, v) in resources.items() if
                         v['resource_type'] not in excluded_types)

    # sort resources with priority
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(compare_deploy_resources))

    success, updated_output = continue_deploy_resources(resources_list, output)
    _LOG.info('AWS resources were deployed successfully')
    if success:
        # apply dynamic changes that uses ARNs
        _LOG.info('Going to apply dynamic changes')
        _apply_dynamic_changes(resources, updated_output)
        _LOG.info('Dynamic changes were applied successfully')

        _LOG.info('Going to apply common tags')
        _apply_tags(output)

    # remove failed output from bucket
    remove_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Going to create deploy output')
    create_deploy_output(bundle_name=bundle_name,
                         deploy_name=deploy_name,
                         output=updated_output,
                         success=success,
                         replace_output=replace_output)
    return success


@exit_on_exception
def remove_failed_deploy_resources(deploy_name, bundle_name,
                                   clean_only_resources=None,
                                   clean_only_types=None,
                                   excluded_resources=None,
                                   excluded_types=None,
                                   clean_externals=None,
                                   preserve_state=None):
    output = new_output = load_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Failed output file was loaded successfully')

    clean_only_resources = _resolve_names(clean_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    # TODO make filter chain
    if clean_only_resources:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          v['resource_name'] in clean_only_resources)

    if excluded_resources:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          v['resource_name'] not in excluded_resources)

    if clean_only_types:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          v['resource_meta'][
                              'resource_type'] in clean_only_types)

    if excluded_types:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          v['resource_meta'][
                              'resource_type'] not in excluded_types)

    if not clean_externals:
        new_output = dict((k, v) for (k, v) in new_output.items() if
                          not v['resource_meta'].get('external'))
    # sort resources with priority
    resources_list = list(new_output.items())
    resources_list.sort(key=cmp_to_key(_compare_clean_resources))

    _LOG.info('Going to clean AWS resources')
    clean_resources(resources_list)

    return _post_remove_output_handling(
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        preserve_state=preserve_state,
        output=output,
        new_output=new_output,
        is_regular_output=False
    )


def _post_remove_output_handling(deploy_name, bundle_name, preserve_state,
                                 output, new_output, is_regular_output):
    if output == new_output:
        if not preserve_state:
            # remove output from bucket
            remove_failed_deploy_output(bundle_name, deploy_name)
    else:
        for key, value in new_output.items():
            output.pop(key)
        create_deploy_output(bundle_name=bundle_name,
                             deploy_name=deploy_name,
                             output=output,
                             success=is_regular_output,
                             replace_output=True)
        return {'operation': PARTIAL_CLEAN_ACTION}


def _apply_dynamic_changes(resources, output):
    from syndicate.core import PROCESSOR_FACADE
    pool = ThreadPoolExecutor(max_workers=5)
    futures = []
    for name, meta in resources.items():
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
                    func = PROCESSOR_FACADE.resource_identifier() \
                        .get(resource_type)
                    if func:
                        resource_output = __find_output_by_resource_name(
                            output, name)
                        identifier = func(name, resource_output)
                        apply_func = PROCESSOR_FACADE.mapping_applier() \
                            .get(change_type)
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


def _apply_tags(output: dict):
    from syndicate.core import RESOURCES_PROVIDER
    tags_resource = RESOURCES_PROVIDER.tags_api()
    tags_resource.apply_tags(output)


def compare_deploy_resources(first, second):
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


def _compare_update_resources(first, second):
    first_resource_type = first[-1]['resource_type']
    second_resource_type = second[-1]['resource_type']
    first_res_priority = UPDATE_RESOURCE_TYPE_PRIORITY[first_resource_type]
    second_res_priority = UPDATE_RESOURCE_TYPE_PRIORITY[second_resource_type]
    return _compare_res(first_res_priority, second_res_priority)


def _compare_res(first_res_priority, second_res_priority):
    if first_res_priority < second_res_priority:
        return -1
    elif first_res_priority > second_res_priority:
        return 1
    else:
        return 0


def _resolve_names(names):
    from syndicate.core import CONFIG
    preset_name_resolution = functools.partial(resolve_resource_name,
                                               prefix=CONFIG.resources_prefix,
                                               suffix=CONFIG.resources_suffix)
    resolve_n_unify_names = lambda collection: set(
        collection + tuple(map(preset_name_resolution, collection)))

    return resolve_n_unify_names(names or tuple())
