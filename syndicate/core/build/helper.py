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
import os
import shutil
import subprocess
import zipfile
from contextlib import closing
from datetime import datetime, date
from pathlib import PurePath, Path
from typing import Union

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import ARTIFACTS_FOLDER
from syndicate.core.helper import build_path

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


def build_py_package_name(lambda_name, lambda_version):
    return '{0}-{1}.zip'.format(lambda_name, lambda_version)


def write_to_zip(
        z: zipfile.ZipFile,
        absfn: str,
        zfn: str,
) -> None:
    """ Helper function to write files to the zip archive. """
    try:
        z.write(absfn, zfn)
    except FileNotFoundError as e:
        mxfn = absfn if len(absfn) > len(zfn) else zfn
        if len(mxfn) > 260:
            raise ValueError(
                f"The path '{mxfn}' exceeds 260 characters (length: {len(mxfn)}"
                f" characters). Was this expected? If not, the file might be "
                f"missing. Please verify the file's existence and consider "
                f"shortening your path if necessary to avoid potential issues "
                f"with path length limitations"
            )
        raise e


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
                write_to_zip(z, absfn, zfn)


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
    raise TypeError("Type %s not serializable" % type(obj))


def resolve_all_bundles_directory():
    from syndicate.core import CONF_PATH
    return build_path(CONF_PATH, ARTIFACTS_FOLDER)


def resolve_bundle_directory(bundle_name):
    return build_path(resolve_all_bundles_directory(), bundle_name)


def assert_bundle_bucket_exists():
    from syndicate.core import CONFIG, CONN
    if not CONN.s3().is_bucket_exists(
            CONFIG.deploy_target_bucket):
        raise AssertionError(
            f'Bundles bucket {CONFIG.deploy_target_bucket} does not exist. '
            f'Please use \'create_deploy_target_bucket\' to create the bucket.'
        )


def construct_deploy_s3_key_path(bundle_name: str, deploy_name: str,
                                 is_failed: bool = False) -> str:
    from syndicate.core import CONFIG
    file_name = f"{deploy_name}{'_failed' if is_failed else ''}.json"
    return PurePath(CONFIG.deploy_target_bucket_key_compound, bundle_name,
                    'outputs', file_name).as_posix()
