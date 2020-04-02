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
import zipfile
from contextlib import closing
from datetime import datetime, date

from syndicate.core.constants import ARTIFACTS_FOLDER
from syndicate.core.helper import build_path


def build_py_package_name(lambda_name, lambda_version):
    return '{0}-{1}.zip'.format(lambda_name, lambda_version)


def zip_dir(basedir, name):
    assert os.path.isdir(basedir)
    with closing(zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED)) as z:
        for root, dirs, files in os.walk(basedir, followlinks=True):
            for fn in files:
                absfn = os.path.join(root, fn)
                zfn = absfn[len(basedir) + len(os.sep):]
                z.write(absfn, zfn)


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
