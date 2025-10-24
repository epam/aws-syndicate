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
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePath
from botocore.exceptions import ClientError

from syndicate.exceptions import ProjectStateError, ConfigurationError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.connection import S3Connection
from syndicate.core.build.helper import _json_serial, resolve_bundle_directory, \
    resolve_all_bundles_directory, assert_bundle_bucket_exists
from syndicate.core.build.meta_processor import validate_deployment_packages, \
    preprocess_tags
from syndicate.core.constants import (ARTIFACTS_FOLDER, BUILD_META_FILE_NAME,
                                      DEFAULT_SEP)
from syndicate.core.helper import build_path, unpack_kwargs

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def build_output_key(bundle_name, deploy_name, is_regular_output):
    return '{0}/outputs/{1}{2}.json'.format(
        bundle_name, deploy_name, '' if is_regular_output else '_failed')


def _backup_deploy_output(filename, output):
    _LOG.info('Wrote file to {0}'.format(filename))
    with open(filename, 'a+') as backup_file:
        backup_file.write(output)
        backup_file.close()


def create_deploy_output(
        bundle_name: str,
        deploy_name: str,
        output: dict,
        success: bool,
        replace_output: bool = False,
) -> None:
    from syndicate.core import CONFIG, CONN
    _LOG.debug('Going to preprocess resources tags in output')
    preprocess_tags(output)
    output_str = json.dumps(output, default=_json_serial)
    key = build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=success)
    key_compound = \
        PurePath(CONFIG.deploy_target_bucket_key_compound, key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket, key_compound) \
            and not replace_output:
        _LOG.warning(f'Output file for deploy {deploy_name} already exists')
    else:
        CONN.s3().put_object(output_str, key_compound,
                             CONFIG.deploy_target_bucket,
                             'application/json')
        _LOG.info(
            f"Output file with name {key} has been "
            f"{'replaced' if replace_output else 'created'}"
        )


def remove_deploy_output(
        bundle_name: str,
        deploy_name: str,
) -> None:
    from syndicate.core import CONFIG, CONN
    key = build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=True)
    key_compound = \
        PurePath(CONFIG.deploy_target_bucket_key_compound, key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket, key_compound):
        CONN.s3().remove_object(CONFIG.deploy_target_bucket, key_compound)
    else:
        _LOG.warning(f'Output file for deploy {deploy_name} does not exist')


def remove_failed_deploy_output(
        bundle_name: str,
        deploy_name: str,
) -> None:
    from syndicate.core import CONFIG, CONN
    key = build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=False)
    key_compound = \
        PurePath(CONFIG.deploy_target_bucket_key_compound, key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket, key_compound):
        _LOG.debug(
            f"Going to remove failed output '{key_compound}' from the bucket "
            f"'{CONFIG.deploy_target_bucket}'"
        )
        CONN.s3().remove_object(CONFIG.deploy_target_bucket, key_compound)
    else:
        _LOG.warning(
            f'Failed output file for deploy {deploy_name} does not exist'
        )


def load_deploy_output(
        bundle_name: str,
        deploy_name: str,
        failsafe: bool = False,
) -> dict | bool:
    """
    :param bundle_name:
    :param deploy_name:
    :param failsafe: False - raise error if no deploy output;
                     True - do not raise an error, return False
    """
    from syndicate.core import CONFIG, CONN
    key = build_output_key(bundle_name=bundle_name,
                            deploy_name=deploy_name,
                            is_regular_output=True)
    key_compound = \
        PurePath(CONFIG.deploy_target_bucket_key_compound, key).as_posix()
    if CONN.s3().is_file_exists(CONFIG.deploy_target_bucket, key_compound):
        output_file = \
            CONN.s3().load_file_body(CONFIG.deploy_target_bucket, key_compound)
        return json.loads(output_file)
    else:
        if failsafe:
            _LOG.warning(
                f'Deploy name {deploy_name} does not exist. '
                f'Failsafe status - {failsafe}'
            )
            return False
        raise ProjectStateError(
            f"Cannot find output file for the deploy name '{deploy_name}'."
        )


def load_failed_deploy_output(bundle_name, deploy_name,
                              failsafe: bool = False):
    """
    :param bundle_name:
    :param deploy_name:
    :param failsafe: False - raise error if no deploy output;
                     True - do not raise an error, return False
    """
    from syndicate.core import CONFIG, CONN
    key = build_output_key(bundle_name=bundle_name,
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
        if failsafe:
            _LOG.warn(f'Deploy name {deploy_name} does not exist. '
                      f'Failsafe status - {failsafe}.')
            return False
        raise ProjectStateError(
            f"Cannot find output file for the deploy name '{deploy_name}'."
        )


def load_latest_deploy_output(failsafe: bool = False):
    from syndicate.core import PROJECT_STATE
    if not PROJECT_STATE.latest_deploy:
        return None, {}
    deploy_name = PROJECT_STATE.latest_deployed_deploy_name
    bundle_name = PROJECT_STATE.latest_deployed_bundle_name
    latest_deploy_status = PROJECT_STATE.latest_deploy.get(
        'is_succeeded', True)

    if latest_deploy_status is True:
        return True, load_deploy_output(bundle_name, deploy_name,
                                        failsafe=failsafe)
    elif latest_deploy_status is False:
        return False, load_failed_deploy_output(bundle_name, deploy_name,
                                                failsafe=failsafe)
    else:
        raise ProjectStateError(
            "The latest deployments' status can't be resolved because of "
            "unexpected status. Please check the parameter 'is_succeeded' "
            "value in the 'latest_deploy' section of the syndicate state "
            "file. Expected value is 'true' or 'false'")


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
    assert_bundle_bucket_exists()
    bundle_folder = bundle_name + DEFAULT_SEP
    key_compound = PurePath(CONFIG.deploy_target_bucket_key_compound,
                            bundle_folder).as_posix()
    return CONN.s3().get_keys_by_prefix(
        CONFIG.deploy_target_bucket,
        key_compound)


def if_bundle_exist_locally(bundle_name):
    bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)
    normalized_bundle_dir = os.path.normpath(bundle_dir)
    if os.path.exists(normalized_bundle_dir):
        _LOG.debug(f'Bundle folder `{normalized_bundle_dir}` exists locally.')
        return True
    return False


def upload_bundle_to_s3(bundle_name, force):
    if if_bundle_exist(bundle_name) and not force:
        raise ProjectStateError(
            f"Bundle name '{bundle_name}' already exists in deploy bucket. "
            f"Please use another bundle name or delete the bundle"
        )

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
        USER_LOG.warning(
            f"Bundles bucket '{CONFIG.deploy_target_bucket}' already exists"
        )
        return False
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
    return True


def load_bundle(bundle_name, src_account_id, src_bucket_region,
                src_bucket_name, role_name):
    from syndicate.core import CONFIG, RESOURCES_PROVIDER
    assert_bundle_bucket_exists()
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
        raise ConfigurationError(
            f"Cannot assume '{role_name}' role. Please verify that the role "
            f"exists and has correct trusted relationships to be assumed from "
            f"'{CONFIG.account_id}' account."
        )
    if not src_s3_conn.is_bucket_exists(src_bucket_name):
        raise ConfigurationError(
            f"'{src_account_id}' account does not have a '{src_bucket_name}' "
            f"bucket. Please verify that you have configured the correct "
            f"bucket name.")
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
            raise ProjectStateError(
                'Bundle name is already exists. Please, verify that have '
                'configured the correct bundle name.'
            )

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


def remove_bundle_dir_locally(bundle_name: str, force_upload: bool):
    if if_bundle_exist_locally(bundle_name) and not force_upload:
        raise ProjectStateError(
            f'Bundle name \'{bundle_name}\' already exists locally. '
            f'Please use another bundle name or delete the existing'
        )
    if force_upload:
        _LOG.info(f'Force upload is enabled, going to check if bundle '
                  f'directory already exists locally.')
        bundle_dir = resolve_bundle_directory(bundle_name=bundle_name)
        normalized_bundle_dir = os.path.normpath(bundle_dir)
        if os.path.exists(normalized_bundle_dir):
            _LOG.warning(f'Going to remove bundle folder '
                         f'`{normalized_bundle_dir}` locally.')
            try:
                shutil.rmtree(normalized_bundle_dir)
            except Exception as e:
                _LOG.error(f'Cannot delete folder {normalized_bundle_dir}')
                raise e
