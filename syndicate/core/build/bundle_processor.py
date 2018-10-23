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

from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor

from syndicate.commons.log_helper import get_logger
from syndicate.connection import S3Connection
from syndicate.core import CONFIG, CONN, sts
from syndicate.core.build.meta_processor import validate_deployment_packages
from syndicate.core.constants import (ARTIFACTS_FOLDER, BUILD_META_FILE_NAME,
                                      DEFAULT_SEP)
from syndicate.core.helper import build_path, unpack_kwargs

_S3_CONN = CONN.s3()

_LOG = get_logger('syndicate.core.build.bundle_processor')


def _build_output_key(bundle_name, deploy_name):
    return '{0}/outputs/{1}.json'.format(bundle_name, deploy_name)


def _build_failed_output_key(bundle_name, deploy_name):
    return '{0}/outputs/{1}_failed.json'.format(bundle_name, deploy_name)


def _backup_deploy_output(filename, output):
    _LOG.info('Wrote file to {0}'.format(filename))
    with open(filename, 'a+') as backup_file:
        backup_file.write(output)
        backup_file.close()


def create_deploy_output(bundle_name, deploy_name, output):
    key = _build_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        _LOG.warn(
            'Output file for deploy {0} already exists.'.format(deploy_name))
    else:
        _S3_CONN.put_object(output, key, CONFIG.deploy_target_bucket,
                            'application/json')


def create_failed_deploy_output(bundle_name, deploy_name, output):
    key = _build_failed_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        _LOG.warn(
            'Failed output file for deploy {0} already exists.'.format(
                deploy_name))
    else:
        _S3_CONN.put_object(output, key, CONFIG.deploy_target_bucket,
                            'application/json')


def remove_deploy_output(bundle_name, deploy_name):
    key = _build_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        _S3_CONN.remove_object(CONFIG.deploy_target_bucket, key)
    else:
        _LOG.warn(
            'Output file for deploy {0} does not exist.'.format(deploy_name))


def remove_failed_deploy_output(bundle_name, deploy_name):
    key = _build_failed_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        _S3_CONN.remove_object(CONFIG.deploy_target_bucket, key)
    else:
        _LOG.warn(
            'Failed output file for deploy {0} does not exist.'.format(
                deploy_name))


def remove_failed_deploy_output(bundle_name, deploy_name):
    key = _build_failed_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        _S3_CONN.remove_object(CONFIG.deploy_target_bucket, key)
    else:
        _LOG.warn(
            'Failed output file for deploy {0} does not exist.'.format(
                deploy_name))


def load_deploy_output(bundle_name, deploy_name):
    key = _build_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        output_file = _S3_CONN.load_file_body(CONFIG.deploy_target_bucket,
                                              key)
        return json.loads(output_file)
    else:
        raise AssertionError('Deploy name {0} does not exist.'
                             ' Cannot find output file.'.format(deploy_name))


def load_failed_deploy_output(bundle_name, deploy_name):
    key = _build_failed_output_key(bundle_name, deploy_name)
    if _S3_CONN.is_file_exists(CONFIG.deploy_target_bucket, key):
        output_file = _S3_CONN.load_file_body(CONFIG.deploy_target_bucket,
                                              key)
        return json.loads(output_file)
    else:
        raise AssertionError('Deploy name {0} does not exist.'
                             ' Cannot find output file.'.format(deploy_name))


def load_meta_resources(bundle_name):
    key = build_path(bundle_name, BUILD_META_FILE_NAME)
    meta_file = _S3_CONN.load_file_body(CONFIG.deploy_target_bucket, key)
    return json.loads(meta_file)


def upload_bundle_to_s3(bundle_name):
    if not _S3_CONN.is_bucket_exists(CONFIG.deploy_target_bucket):
        raise AssertionError("Bundles bucket {0} does not exist "
                             " Please use 'create_deploy_target_bucket' to "
                             "create the bucket.".format(
            CONFIG.deploy_target_bucket))
    bundle_folder = bundle_name + DEFAULT_SEP
    if _S3_CONN.get_keys_by_prefix(CONFIG.deploy_target_bucket, bundle_folder):
        raise AssertionError('Bundle name {0} already exists '
                             'in deploy bucket. Please use another bundle '
                             'name or delete the bundle'.format(bundle_name))

    bundle_path = build_path(CONFIG.project_path, ARTIFACTS_FOLDER,
                             bundle_name)
    build_meta_path = build_path(bundle_path, BUILD_META_FILE_NAME)
    meta_resources = json.load(open(build_meta_path))
    validate_deployment_packages(meta_resources)
    _LOG.info('Bundle was validated successfully')
    paths = []
    for root, dirs, file_names in os.walk(bundle_path):
        for file_name in file_names:
            paths.append(file_name)
    # paths = artifact_paths(meta_resources)
    # paths.append(build_path(bundle_name, BUILD_META_FILE_NAME))
    executor = ThreadPoolExecutor(max_workers=10)
    futures = []
    for path in paths:
        if 'output/' not in path:
            path_to_package = build_path(CONFIG.project_path, ARTIFACTS_FOLDER,
                                         bundle_name, path)
            _LOG.debug('Going to upload file: {0}'.format(path_to_package))
            arg = {
                'path': build_path(bundle_name, path),
                'path_to_package': path_to_package
            }
            futures.append(executor.submit(_put_package_to_s3, arg))
    return futures


def create_bundles_bucket():
    if _S3_CONN.is_bucket_exists(CONFIG.deploy_target_bucket):
        _LOG.info('Bundles bucket {0} already exists'.format(
            CONFIG.deploy_target_bucket))
    else:
        _LOG.info(
            'Bundles bucket {0} does not exist. Creating bucket..'.format(
                CONFIG.deploy_target_bucket))
        _S3_CONN.create_bucket(bucket_name=CONFIG.deploy_target_bucket,
                               location=CONFIG.region)
        _LOG.info('{0} bucket created successfully'.format(
            CONFIG.deploy_target_bucket))


def load_bundle(bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name):
    if not _S3_CONN.is_bucket_exists(CONFIG.deploy_target_bucket):
        raise AssertionError("Bundles bucket {0} does not exist "
                             " Please use 'create_deploy_target_bucket' to "
                             "create the bucket.".format(
            CONFIG.deploy_target_bucket))
    try:
        _LOG.debug(
            'Going to assume {0} role from {1} account'.format(role_name,
                                                               src_account_id))
        credentials = sts.get_temp_credentials(role_name, src_account_id, 3600)
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
    artifacts_names = map(lambda meta: meta['Key'], objects)
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
    _S3_CONN.upload_single_file(path_to_package, path,
                                CONFIG.deploy_target_bucket)
