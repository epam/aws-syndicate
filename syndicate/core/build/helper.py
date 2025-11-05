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
import functools
import os
import shutil
import subprocess
import zipfile
from contextlib import closing
from datetime import datetime, date
from pathlib import PurePath, Path
from typing import Union

from syndicate.exceptions import InvalidValueError, InvalidTypeError, \
    ConfigurationError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import ARTIFACTS_FOLDER, CACHE_DIR
from syndicate.core.helper import build_path

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def build_py_package_name(lambda_name, lambda_version):
    return '{0}-{1}.zip'.format(lambda_name, lambda_version)


def file_path_length_checker(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            path_from_e = e.filename
            if len(path_from_e) < 260:
                raise e
            raise InvalidValueError(
                f"The path '{path_from_e}' has exceeded the 260-character "
                f"length (current length: '{len(path_from_e)}'). This may "
                f"have caused the FileNotFoundError. Please verify that the "
                f"file exists and consider shortening the path or increasing "
                f"the maximum path length allowed by the operating system."
            )
    return wrapper


@file_path_length_checker
def zip_dir(
        basedir: str,
        name: str,
        archive_subfolder: str = None,
) -> None:
    """ Compresses a directory into a zip file """
    assert os.path.isdir(basedir), \
        f"The specified base directory does not exist: {basedir}"

    with closing(zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED)) as z:
        for root, dirs, files in os.walk(basedir, followlinks=True):
            archive_root = os.path.join(
                archive_subfolder, os.path.relpath(root, basedir)) \
                if archive_subfolder else os.path.relpath(root, basedir)
            for fn in files:
                absfn = os.path.normpath(os.path.join(root, fn))
                zfn = os.path.normpath(os.path.join(archive_root, fn))
                z.write(absfn, zfn)


def merge_zip_files(zip1_path: str, zip2_path: str, output_path: str,
                    output_subfolder:str=None):
    """
    Merge two ZIP files into a new ZIP file.
    Files from zip2_path overwrite those from zip1_path in case of name conflicts.
    """
    with zipfile.ZipFile(output_path, 'w') as output_zip:
        for zip_path in [zip1_path, zip2_path]:
            if not os.path.isfile(zip_path):
                _LOG.warning(
                    f"Zip file '{zip_path}' does not exist or is not file. "
                    f"Skipping.")
                continue
            with zipfile.ZipFile(zip_path, 'r') as input_zip:
                for file_info in input_zip.infolist():
                    data = input_zip.read(file_info.filename)
                    new_path = (
                        os.path.join(output_subfolder, file_info.filename) if
                        output_subfolder else file_info.filename
                    )

                    normalized_path = os.path.normpath(new_path)
                    final_path = normalized_path.replace(
                        os.sep,'/') if os.sep != '/' else normalized_path

                    output_zip.writestr(final_path, data)


def run_external_command(command: list):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True)

    return result.returncode, result.stdout, result.stderr


def remove_dir(path: Union[str, Path]):
    removed = False
    while not removed:
        _LOG.info(f'Trying to remove "{path}"')
        try:
            shutil.rmtree(path)
            removed = True
        except Exception as e:
            removed = True
            _LOG.warn(f'An error "{e}" occurred while '
                      f'removing artifacts "{path}"')


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise InvalidTypeError(f"Type '{type(obj).__name__}' is not serializable")


def resolve_all_bundles_directory():
    from syndicate.core import CONF_PATH
    return build_path(CONF_PATH, ARTIFACTS_FOLDER)


def resolve_bundle_directory(bundle_name):
    return build_path(resolve_all_bundles_directory(), bundle_name)

def resolve_bundles_cache_directory():
    return build_path(resolve_all_bundles_directory(), CACHE_DIR)


def assert_bundle_bucket_exists() -> None:
    from syndicate.core import CONFIG, CONN
    if not CONN.s3().is_bucket_exists(CONFIG.deploy_target_bucket):
        raise ConfigurationError(
            f"Bundles bucket '{CONFIG.deploy_target_bucket}' does not exist. "
            f"Please use 'create_deploy_target_bucket' to create the bucket."
        )


def construct_deploy_s3_key_path(bundle_name: str, deploy_name: str,
                                 is_failed: bool = False) -> str:
    from syndicate.core import CONFIG
    file_name = f"{deploy_name}{'_failed' if is_failed else ''}.json"
    return PurePath(CONFIG.deploy_target_bucket_key_compound, bundle_name,
                    'outputs', file_name).as_posix()
