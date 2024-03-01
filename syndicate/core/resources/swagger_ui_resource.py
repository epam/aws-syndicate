"""
    Copyright 2024 EPAM Systems, Inc.

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
from pathlib import PurePath
from shutil import rmtree
from zipfile import ZipFile

from syndicate.commons import deep_get
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import SWAGGER_UI_ARTIFACT_NAME_TEMPLATE, \
    ARTIFACTS_FOLDER
from syndicate.core.helper import build_path, unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

INDEX_FILE_NAME = 'index.html'

_LOG = get_logger('syndicate.core.resources.swagger_ui_resource')
USER_LOG = get_user_logger()


class SwaggerUIResource(BaseResource):

    def __init__(self, s3_conn, deploy_target_bucket, region,
                 account_id) -> None:
        from syndicate.core import CONF_PATH
        self.s3_conn = s3_conn
        self.deploy_target_bucket = deploy_target_bucket
        self.region = region
        self.account_id = account_id
        self.conf_path = CONF_PATH

    def create_update_swagger_ui(self, args):
        return self.create_pool(self._create_update_swagger_ui_from_meta, args)

    def remove_swagger_ui(self, args):
        return self.create_pool(self._remove_swagger_ui, args)

    @unpack_kwargs
    def _create_update_swagger_ui_from_meta(self, name, meta):
        artifact_file_name = SWAGGER_UI_ARTIFACT_NAME_TEMPLATE.format(
            name=name)
        artifact_dir = PurePath(self.conf_path, ARTIFACTS_FOLDER,
                                name).as_posix()
        target_bucket = meta.get('target_bucket')
        if not target_bucket:
            raise AssertionError(f'Target bucket for Swagger UI \'{name}\' is '
                                 f'absent in resource meta')
        if not self.s3_conn.is_bucket_exists(target_bucket):
            raise AssertionError(f'Target bucket \'{target_bucket}\' for '
                                 f'Swagger UI \'{name}\' doesn\'t exists')
        bundle_path = meta.get('artifact_path')
        if not bundle_path:
            raise AssertionError(f'Can\'t resolve bundle name')
        if '/' in self.deploy_target_bucket:
            deploy_bucket_name = self.deploy_target_bucket.split('/', 1)[0]
            artifact_src_path = self.deploy_target_bucket.split('/', 1)[1] + \
                bundle_path + '/' + artifact_file_name
        else:
            deploy_bucket_name = self.deploy_target_bucket
            artifact_src_path = bundle_path + '/' + artifact_file_name

        _LOG.info(f'Downloading an artifact for Swagger UI \'{name}\'')
        artifact = self.s3_conn.download_to_file(
            bucket_name=deploy_bucket_name,
            key=artifact_src_path)

        extract_to = build_path(artifact_dir, name)
        with ZipFile(artifact, 'r') as zf:
            zf.extractall(extract_to)

        _LOG.info(f'Uploading files for Swagger UI \'{name}\' to target '
                  f'bucket \'{target_bucket}\'')
        for file in os.listdir(extract_to):
            self.s3_conn.upload_single_file(path=PurePath(extract_to,
                                                          file).as_posix(),
                                            key=file,
                                            bucket=target_bucket)

        _LOG.info(f'Removing temporary directory \'{artifact_dir}\'')
        rmtree(artifact_dir)

        return {
            f'arn:aws-syndicate:{self.region}:{self.account_id}:{name}':
                build_description_obj(None, name, meta)
        }

    @unpack_kwargs
    def _remove_swagger_ui(self, arn, config):
        resource_name = arn.split(':')[-1]
        target_bucket = deep_get(config, ['resource_meta', 'target_bucket'])
        if not self.s3_conn.is_bucket_exists(target_bucket):
            USER_LOG.info(f'Target bucket with name \'{target_bucket}\' not '
                          f'found')
        else:
            self.s3_conn.remove_object(bucket_name=target_bucket,
                                       file_name=INDEX_FILE_NAME)
            self.s3_conn.remove_object(
                bucket_name=target_bucket,
                file_name=SWAGGER_UI_ARTIFACT_NAME_TEMPLATE.format(
                    name=resource_name))
            USER_LOG.info(f'Swagger UI \'{resource_name}\' removed')

