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
import copy
import functools
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor
from functools import cmp_to_key

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.build.bundle_processor import (create_deploy_output,
                                                   load_deploy_output,
                                                   load_failed_deploy_output,
                                                   load_meta_resources,
                                                   remove_failed_deploy_output,
                                                   load_latest_deploy_output)
from syndicate.core.build.meta_processor import (resolve_meta,
                                                 populate_s3_paths,
                                                 resolve_resource_name)
from syndicate.core.constants import (BUILD_META_FILE_NAME,
                                      CLEAN_RESOURCE_TYPE_PRIORITY,
                                      DEPLOY_RESOURCE_TYPE_PRIORITY,
                                      UPDATE_RESOURCE_TYPE_PRIORITY,
                                      PARTIAL_CLEAN_ACTION)
from syndicate.core.helper import exit_on_exception, prettify_json

BUILD_META = 'build_meta'
DEPLOYMENT_OUTPUT = 'deployment_output'

_LOG = get_logger('syndicate.core.build.deployment_processor')
USER_LOG = get_user_logger()


def _process_resources(resources, handlers_mapping, pass_context=False,
                       output=None):
    output = output or {}
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
                response = func(args)
                process_response(response=response, output=output)

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
            process_response(response=response, output=output)

        return True, output
    except Exception as e:
        USER_LOG.exception('Error occurred while {0} '
                           'resource creating: {1}'.format(resource_type,
                                                           str(e)))
        return False, output


def _process_resources_with_dependencies(resources, handlers_mapping,
                                         pass_context=False,
                                         overall_resources=None, output=None,
                                         current_resource_type=None,
                                         run_count=0):
    overall_resources = overall_resources or resources
    output = output or {}
    try:
        for res_name, res_meta in resources:
            args = []
            resource_type = res_meta['resource_type']
            if res_meta.get('processed'):
                _LOG.debug(f"Processing of '{resource_type}' '{res_name}' "
                           f"skipped. Resource already processed")
                continue

            if run_count >= len(overall_resources):
                raise RecursionError(
                    "An infinite loop detected in resource dependencies")

            run_count += 1

            dependencies = [item['resource_name'] for item in
                            res_meta.get('dependencies', [])]
            _LOG.debug(f"'{resource_type}' '{res_name}' depends on resources: "
                       f"{dependencies}")
            # Order of items in depends_on_resources is important!
            depends_on_resources = []
            for dep_res_name in dependencies:
                for overall_res_name, overall_res_meta in overall_resources:
                    if overall_res_name == dep_res_name:
                        depends_on_resources.append((overall_res_name,
                                                    overall_res_meta))

            if depends_on_resources:
                _LOG.info(
                    f"Processing '{resource_type}' '{res_name}' dependencies "
                    f"{prettify_json(res_meta['dependencies'])}")

                success, output = _process_resources_with_dependencies(
                    resources=depends_on_resources,
                    handlers_mapping=handlers_mapping,
                    pass_context=pass_context,
                    overall_resources=overall_resources,
                    output=output,
                    current_resource_type=current_resource_type,
                    run_count=run_count)

                if not success:
                    return False, output

            args.append(_build_args(name=res_name,
                                    meta=res_meta,
                                    context=output,
                                    pass_context=pass_context))
            if current_resource_type != resource_type:
                USER_LOG.info(f'Processing {resource_type} resources')
                current_resource_type = resource_type
            func = handlers_mapping[resource_type]
            response = func(args)
            process_response(response=response, output=output)

            res_meta['processed'] = True
            overall_res_index = overall_resources.index(
                (res_name, res_meta))
            overall_resources[overall_res_index][-1]['processed'] = True

        return True, output
    except Exception as e:
        if 'An infinite loop' in str(e):
            USER_LOG.error(e.args[0])
        else:
            USER_LOG.exception(f"Error occurred while '{resource_type}' "
                               f"resource creating: {str(e)}")
        return False, output


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


def deploy_resources(resources, output=None):
    from syndicate.core import PROCESSOR_FACADE
    process_with_dependency = False

    for _, res_meta in resources:
        res_priority = DEPLOY_RESOURCE_TYPE_PRIORITY[res_meta['resource_type']]
        dependencies = res_meta.get('dependencies', [])
        dep_priorities = [
            DEPLOY_RESOURCE_TYPE_PRIORITY[item['resource_type']] for item in
            dependencies]

        if dep_priorities:
            if max(dep_priorities) >= res_priority:
                process_with_dependency = True
                break

    if process_with_dependency:
        USER_LOG.warn(
            'Resource dependency with higher deployment priority from a '
            'resource with equal or lower deployment priority detected. '
            'Deployment may take a little bit more time than usual.')

        return _process_resources_with_dependencies(
            resources=resources,
            handlers_mapping=PROCESSOR_FACADE.create_handlers(),
            output=output)

    return _process_resources(
        resources=resources,
        handlers_mapping=PROCESSOR_FACADE.create_handlers(),
        output=output)


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


def continue_deploy_resources(resources, failed_output):
    new_output = {}
    for arn, meta in failed_output.items():
        for resource_name, resource_meta in resources:
            if resource_name == meta['resource_name']:
                new_output[arn] = meta
                resources.remove((resource_name, resource_meta))

    if len(new_output) == len(resources):
        return True, failed_output

    return deploy_resources(resources, new_output)


def process_response(response, output: dict):

    if isinstance(response, dict):
        output.update(response)
    elif isinstance(response, tuple):
        result, exceptions = response
        if result:
            output.update(result)
        raise Exception(exceptions[0])

    return output


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
                                replace_output=False,
                                rollback_on_error=False):

    from syndicate.core import PROJECT_STATE
    latest_deploy_name = PROJECT_STATE.latest_deploy.get('deploy_name')
    latest_bundle_name = PROJECT_STATE.latest_deploy.get('bundle_name')
    latest_deploy_status = PROJECT_STATE.latest_deploy.get('operation_status')

    if latest_deploy_status is False:
        message = (f"Your last deployment with deploy name: "
                   f"{latest_deploy_name} and deploy bundle: "
                   f"{latest_bundle_name} failed, you can either clean "
                   f"resources with `syndicate clean` or continue deployment"
                   f" with `syndicate deploy --continue_deploy`.")
        raise AssertionError(message)

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

    expected_external_resources = {key: value for key, value in
                                   resources.items() if value.get('external')}
    if expected_external_resources:
        _compare_external_resources(expected_external_resources)
        _LOG.info('External resources were matched successfully')

    resources = _filter_resources(
        resources_meta=resources,
        resource_names=deploy_only_resources,
        resource_types=deploy_only_types,
        exclude_names=excluded_resources,
        exclude_types=excluded_types
    )

    _LOG.debug('Going to create: {0}'.format(prettify_json(resources)))

    # sort resources with priority
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(compare_deploy_resources))

    _LOG.info('Going to deploy AWS resources')
    success, output = deploy_resources(resources_list)

    if not success:
        if rollback_on_error is True:
            USER_LOG.info(
                "Deployment failed, `rollback_on_error` is enabled,"
                " going to clean resources that have been deployed during"
                " deployment process.")
            output_resources_list = list(output.items())
            output_resources_list.sort(
                key=cmp_to_key(_compare_clean_resources))

            if latest_deploy_output:
                deploy_output_names = list(latest_deploy_output.keys())
                rollback_resources_list =\
                    [resource for resource in output_resources_list if
                     resource[0] not in deploy_output_names]
                clean_resources(rollback_resources_list)
            else:
                clean_resources(output_resources_list)

        else:
            USER_LOG.info('Going to create deploy output')
            create_deploy_output(bundle_name=bundle_name,
                                 deploy_name=deploy_name,
                                 output={**output, **latest_deploy_output},
                                 success=success,
                                 replace_output=replace_output)
    else:
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

    if not (success is False and rollback_on_error is True):
        USER_LOG.info('Deploy output for {0} was created.'.format(deploy_name))
    return success


@exit_on_exception
def update_deployment_resources(bundle_name, deploy_name, replace_output=False,
                                update_only_types=None,
                                update_only_resources=None,
                                excluded_resources=None,
                                excluded_types=None):
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

    resources = dict((k, v) for (k, v) in resources.items() if
                     v['resource_type'] in
                     PROCESSOR_FACADE.update_handlers().keys())

    resources = _filter_resources(
        resources_meta=resources,
        resource_names=update_only_resources,
        resource_types=update_only_types,
        exclude_names=excluded_resources,
        exclude_types=excluded_types
    )

    _LOG.debug('Going to update the following resources: {0}'.format(
        prettify_json(resources)))
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(_compare_update_resources))

    success, output = update_resources(resources_list)

    create_deploy_output(bundle_name=bundle_name,
                         deploy_name=deploy_name,
                         output=output,
                         success=success,
                         replace_output=replace_output)
    return success


@exit_on_exception
def remove_deployment_resources(deploy_name, bundle_name,
                                clean_only_resources=None,
                                clean_only_types=None,
                                excluded_resources=None,
                                excluded_types=None,
                                clean_externals=None,
                                preserve_state=None):

    is_regular_output = True
    try:
        output = new_output = load_deploy_output(bundle_name, deploy_name)
        _LOG.info('Output file was loaded successfully')
    except AssertionError:
        try:
            output = new_output = load_failed_deploy_output(
                bundle_name, deploy_name
            )
            is_regular_output = False
        except AssertionError as e:
            return e

    clean_only_resources = _resolve_names(clean_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    if clean_externals:
        new_output = {
            k: v for k, v in new_output.items() if
            v['resource_meta'].get('external')
        }

    new_output = _filter_resources(
        resources_meta=new_output,
        resources_meta_type=DEPLOYMENT_OUTPUT,
        resource_names=clean_only_resources,
        resource_types=clean_only_types,
        exclude_names=excluded_resources,
        exclude_types=excluded_types
    )
    # sort resources with priority
    resources_list = list(new_output.items())
    resources_list.sort(key=cmp_to_key(_compare_clean_resources))
    _LOG.debug(f'Resources to delete: {prettify_json(resources_list)}')
    USER_LOG.info('Going to clean AWS resources')
    clean_resources(resources_list)
    # remove new_output from bucket
    return _post_remove_output_handling(
        deploy_name=deploy_name,
        bundle_name=bundle_name,
        preserve_state=preserve_state,
        output=output,
        new_output=new_output,
        is_regular_output=is_regular_output
    )


@exit_on_exception
def continue_deployment_resources(deploy_name, bundle_name,
                                  deploy_only_resources=None,
                                  deploy_only_types=None,
                                  excluded_resources=None,
                                  excluded_types=None,
                                  replace_output=False):
    from syndicate.core import PROJECT_STATE
    latest_deploy_name = PROJECT_STATE.latest_deploy.get('deploy_name')
    latest_bundle_name = PROJECT_STATE.latest_deploy.get('bundle_name')
    latest_deploy_status = PROJECT_STATE.latest_deploy.get('operation_status')

    if latest_deploy_status is True:
        raise AssertionError(f"Your last deployment with deploy name:"
                             f" {latest_deploy_name} and deploy bundle:"
                             f" {latest_bundle_name} was successful,"
                             f" you cannot execute the `continue deploy` "
                             f"command.")

    failed_output = load_failed_deploy_output(
        bundle_name=latest_bundle_name, deploy_name=latest_deploy_name
    )
    _LOG.info('Failed output file was loaded successfully')

    resources = load_meta_resources(bundle_name)
    _LOG.debug('{0} file was loaded successfully'.format(BUILD_META_FILE_NAME))

    resources = resolve_meta(resources)
    _LOG.debug('Names were resolved')
    resources = populate_s3_paths(resources, bundle_name)
    _LOG.debug('Artifacts s3 paths were resolved')

    deploy_only_resources = _resolve_names(deploy_only_resources)
    excluded_resources = _resolve_names(excluded_resources)
    _LOG.info(
        'Prefixes and suffixes of any resource names have been resolved.')

    resources = _filter_resources(
        resources_meta=resources,
        resource_names=deploy_only_resources,
        resource_types=deploy_only_types,
        exclude_names=excluded_resources,
        exclude_types=excluded_types
    )

    _LOG.debug('Going to create: {0}'.format(prettify_json(resources)))

    # sort resources with priority
    resources_list = list(resources.items())
    resources_list.sort(key=cmp_to_key(compare_deploy_resources))

    success, updated_output = continue_deploy_resources(
        resources=resources_list, failed_output=failed_output)
    _LOG.info('AWS resources were deployed successfully')
    if success:
        # apply dynamic changes that uses ARNs
        _LOG.info('Going to apply dynamic changes')
        _apply_dynamic_changes(resources, updated_output)
        _LOG.info('Dynamic changes were applied successfully')

        _LOG.info('Going to apply common tags')
        _apply_tags(updated_output)

    # remove failed output from bucket
    remove_failed_deploy_output(bundle_name, deploy_name)
    _LOG.info('Going to create deploy output')
    create_deploy_output(bundle_name=bundle_name,
                         deploy_name=deploy_name,
                         output=updated_output,
                         success=success,
                         replace_output=replace_output)
    return success


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


def _filter_resources(resources_meta, resources_meta_type=BUILD_META,
                      resource_names=None, resource_types=None,
                      exclude_names=None, exclude_types=None):
    resource_names = set() if resource_names is None else set(resource_names)
    resource_types = set() if resource_types is None else set(resource_types)
    exclude_names = set() if exclude_names is None else set(exclude_names)
    exclude_types = set() if exclude_types is None else set(exclude_types)

    _LOG.debug(f"Include resources by name: {list(resource_names) or 'All'}")
    _LOG.debug(f"Include resources by type: {list(resource_types) or 'All'}")
    _LOG.debug(f"Exclude resources by name: {list(exclude_names) or 'None'}")
    _LOG.debug(f"Exclude resources by type: {list(exclude_types) or 'None'}")

    if not any([resource_names, resource_types]):
        filtered = resources_meta
    else:
        if resources_meta_type == BUILD_META:
            filtered = {
                k: v for k, v in resources_meta.items()
                if k in resource_names or v['resource_type'] in resource_types
            }
        elif resources_meta_type == DEPLOYMENT_OUTPUT:
            filtered = {
                k: v for k, v in resources_meta.items()
                if v['resource_name'] in resource_names
                or v['resource_meta']['resource_type'] in resource_types
            }

    for k, v, in copy.deepcopy(filtered).items():
        if resources_meta_type == BUILD_META:
            if k in exclude_names or v['resource_type'] in exclude_types:
                filtered.pop(k)
        elif resources_meta_type == DEPLOYMENT_OUTPUT:
            if (v['resource_name'] in exclude_names
                    or v['resource_meta']['resource_type'] in exclude_types):
                filtered.pop(k)

    return filtered
