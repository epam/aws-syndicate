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
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePath
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection import S3Connection
from syndicate.core.build.helper import _json_serial, resolve_bundle_directory, \
    resolve_all_bundles_directory
from syndicate.core.build.meta_processor import validate_deployment_packages
from syndicate.core.constants import (ARTIFACTS_FOLDER, BUILD_META_FILE_NAME,
                                      DEFAULT_SEP)
from syndicate.core.helper import build_path, unpack_kwargs

_LOG = get_logger('syndicate.core.build.bundle_processor')


def _build_output_key(bundle_name, deploy_name, is_regular_output):
    return '{0}/outputs/{1}{2}.json'.format(
        bundle_name, deploy_name, '' if is_regular_output else '_failed')


def _backup_deploy_output(filename, output):
    _LOG.info('Wrote file to {0}'.format(filename))
    with open(filename, 'a+') as backup_file:
        backup_file.write(output)
        backup_file.close()


def create_deploy_output(bundle_name, deploy_name, output, success,
                         replace_output=False):
    from syndicate.core import CONFIG, CONN
    output_str = json.dumps(output, default=_json_serial)
    key = _build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=success)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket,
                                key_compound) and not replace_output:
        _LOG.warn(
            'Output file for deploy {0} already exists.'.format(deploy_name))
    else:
        CONN.s3().put_object(output_str, key_compound,
                             CONFIG.deploy_target_bucket,
                             'application/json')
        _LOG.info('Output file with name {} has been {}'.format(
            key, 'replaced' if replace_output else 'created'))

def remove_deploy_output(bundle_name, deploy_name):
    from syndicate.core import CONFIG, CONN
    key = _build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=True)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket,
                                key_compound):
        CONN.s3().remove_object(CONFIG.deploy_target_bucket, key_compound)
    else:
        _LOG.warn(
            'Output file for deploy {0} does not exist.'.format(deploy_name))


def remove_failed_deploy_output(bundle_name, deploy_name):
    from syndicate.core import CONFIG, CONN
    key = _build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=False)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket,
                                key_compound):
        CONN.s3().remove_object(CONFIG.deploy_target_bucket, key_compound)
    else:
        _LOG.warn(
            'Failed output file for deploy {0} does not exist.'.format(
                deploy_name))


def load_deploy_output(bundle_name, deploy_name):
    from syndicate.core import CONFIG, CONN
    key = _build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=True)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    if CONN.s3().is_file_exists(
            CONFIG.deploy_target_bucket, key_compound):
        output_file = CONN.s3().load_file_body(
            CONFIG.deploy_target_bucket, key_compound)
        return json.loads(output_file)
    else:
        raise AssertionError('Deploy name {0} does not exist.'
                             ' Cannot find output file.'.format(deploy_name))


def load_failed_deploy_output(bundle_name, deploy_name):
    from syndicate.core import CONFIG, CONN
    key = _build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=False)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket,
                                key_compound):
        output_file = CONN.s3().load_file_body(
            CONFIG.deploy_target_bucket,
            key_compound)
        return json.loads(output_file)
    else:
        raise AssertionError('Deploy name {0} does not exist.'
                             ' Cannot find output file.'.format(deploy_name))


def load_meta_resources(bundle_name):
    from syndicate.core import CONFIG, CONN
    key = build_path(bundle_name, BUILD_META_FILE_NAME)
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            key).as_posix()
    meta_file = CONN.s3().load_file_body(
        CONFIG.deploy_target_bucket, key_compound)
    return json.loads(meta_file)


def if_bundle_exist(bundle_name):
    from syndicate.core import CONFIG, CONN
    _assert_bundle_bucket_exists()
    bundle_folder = bundle_name + DEFAULT_SEP
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            bundle_folder).as_posix()
    return CONN.s3().get_keys_by_prefix(
        CONFIG.deploy_target_bucket,
        key_compound)


def upload_bundle_to_s3(bundle_name, force):
    if if_bundle_exist(bundle_name) and not force:
        raise AssertionError('Bundle name {0} already exists '
                             'in deploy bucket. Please use another bundle '
                             'name or delete the bundle'.format(bundle_name))

    bundle_path = resolve_bundle_directory(bundle_name=bundle_name)
    build_meta_path = build_path(bundle_path, BUILD_META_FILE_NAME)
    meta_resources = json.load(open(build_meta_path))
    validate_deployment_packages(bundle_path=resolve_all_bundles_directory(),
                                 meta_resources=meta_resources)
    _LOG.info('Bundle was validated successfully')
    paths = []
    for root, dirs, file_names in os.walk(bundle_path):
        for file_name in file_names:
            paths.append(file_name)
    executor = ThreadPoolExecutor(max_workers=10)
    futures = []
    for path in paths:
        if 'output/' not in path:
            path_to_package = build_path(bundle_path, path)
            _LOG.debug('Going to upload file: {0}'.format(path_to_package))
            arg = {
                'path': build_path(bundle_name, path),
                'path_to_package': path_to_package
            }
            futures.append(executor.submit(_put_package_to_s3, arg))
    return futures


def create_bundles_bucket():
    from syndicate.core import CONFIG, CONN
    if CONN.s3().is_bucket_exists(CONFIG.deploy_target_bucket):
        _LOG.info('Bundles bucket {0} already exists'.format(
            CONFIG.deploy_target_bucket))
    else:
        _LOG.info(
            'Bundles bucket {0} does not exist. Creating bucket..'.format(
                CONFIG.deploy_target_bucket))
        CONN.s3().create_bucket(
            bucket_name=CONFIG.deploy_target_bucket,
            location=CONFIG.region)
        CONN.s3().put_public_access_block(CONFIG.deploy_target_bucket)
        _LOG.info('{0} bucket created successfully'.format(
            CONFIG.deploy_target_bucket))


def load_bundle(bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name):
    from syndicate.core import CONFIG, RESOURCES_PROVIDER
    _assert_bundle_bucket_exists()
    try:
        _LOG.debug(
            'Going to assume {0} role from {1} account'.format(role_name,
                                                               src_account_id))
        credentials = RESOURCES_PROVIDER.sts().get_temp_credentials(
            role_name, src_account_id, 3600)
        access_key = credentials['AccessKeyId']
        secret_key = credentials['SecretAccessKey']
        session_token = credentials['SessionToken']
        src_s3_conn = S3Connection(region=src_bucket_region,
                                   aws_access_key_id=access_key,
                                   aws_secret_access_key=secret_key,
                                   aws_session_token=session_token)
        _LOG.debug('Credentials were assumed successfully')
    except ClientError:
        raise AssertionError('Cannot assume {0} role. Please verify that '
                             'the role exists and has correct trusted '
                             'relationships to be assumed from {1}'
                             ' account.'.format(role_name, CONFIG.account_id))
    if not src_s3_conn.is_bucket_exists(src_bucket_name):
        raise AssertionError(
            "{0} account does not have a {1} bucket. Please verify that you "
            "have configured the correct bucket name.".format(src_account_id,
                                                              src_bucket_name))
    _LOG.info('Going to find S3 keys for bundle: {0}'.format(bundle_name))
    objects = src_s3_conn.list_objects(bucket_name=src_bucket_name,
                                       prefix=bundle_name)
    artifacts_names = [meta['Key'] for meta in objects]
    _LOG.info('Found {0} artifacts: {1}'.format(len(artifacts_names),
                                                artifacts_names))

    bundle_path = build_path(CONFIG.project_path, ARTIFACTS_FOLDER,
                             bundle_name)
    for dirpath, dirnames, files in os.walk(bundle_path):
        if files:
            raise AssertionError('Bundle name is already exists. '
                                 'Please, verify that have configured '
                                 'the correct bundle name.')

    # TODO create_pool can be used
    executor = ThreadPoolExecutor(max_workers=10)
    futures = []
    for key in artifacts_names:
        arg = {
            'conn': src_s3_conn,
            'bucket_name': src_bucket_name,
            'key': key,
            'path': build_path(CONFIG.project_path, ARTIFACTS_FOLDER, key)
        }
        futures.append(executor.submit(_download_package_from_s3, arg))
    return futures


@unpack_kwargs
def _download_package_from_s3(conn, bucket_name, key, path):
    conn.download_file(bucket_name, key, path)


@unpack_kwargs
def _put_package_to_s3(path, path_to_package):
    from syndicate.core import CONN, CONFIG
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            path).as_posix()
    CONN.s3().upload_single_file(path_to_package, key_compound,
                                 CONFIG.deploy_target_bucket)


def _assert_bundle_bucket_exists():
    from syndicate.core import CONFIG, CONN
    if not CONN.s3().is_bucket_exists(
            CONFIG.deploy_target_bucket):
        raise AssertionError("Bundles bucket {0} does not exist."
                             " Please use 'create_deploy_target_bucket' to "
                             "create the bucket."
                             .format(CONFIG.deploy_target_bucket))
