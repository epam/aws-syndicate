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
import io
import json
import os
import posixpath
from functools import cached_property
from pathlib import PurePath
from shutil import rmtree
from typing import Optional
from zipfile import ZipFile

from syndicate.commons import deep_get
from syndicate.exceptions import ResourceNotFoundError, ParameterError
from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core.constants import ARTIFACTS_FOLDER, S3_PATH_NAME, \
    SWAGGER_UI_SPEC_NAME_TEMPLATE, API_GATEWAY_TYPE, RESOURCE_TYPE_PARAM, \
    RESOURCE_NAME_PARAM, PARAMETER_NAME_PARAM, PARAMETER_TYPE_PARAM
from syndicate.core.helper import build_path, unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

INDEX_FILE_NAME = 'index.html'
X_SYNDICATE_SERVER_PARAM = 'x-syndicate-server'
# example:
# "x-syndicate-server": {
#     "resource_name": "sdct-at-api-gw",
#     "resource_type": "api_gateway",
#     "parameter_name": "stage_name"
#     "parameter_name": "api"
#   }

S3_LINK_TEMPLATE = 'http://{target_bucket}.s3-website.{region}.amazonaws.com'
API_LINK_TEMPLATE = 'https://{api_id}.execute-api.{region}.amazonaws.com/{stage_name}'

_LOG = get_logger(__name__)
USER_LOG = get_user_logger()


class SwaggerUIResource(BaseResource):

    def __init__(self, s3_conn, deploy_target_bucket,
                 deploy_target_bucket_key_compound, region,
                 account_id, extended_prefix_mode, prefix, suffix) -> None:
        from syndicate.core import CONF_PATH, RESOURCES_PROVIDER
        self.s3_conn = s3_conn
        self.deploy_target_bucket = deploy_target_bucket
        self.deploy_target_bucket_key_compound = \
            deploy_target_bucket_key_compound
        self.region = region
        self.account_id = account_id
        self.extended_prefix_mode = extended_prefix_mode
        self.prefix = prefix
        self.suffix = suffix
        self.conf_path = CONF_PATH
        self.resources_provider = RESOURCES_PROVIDER

    @cached_property
    def server_api_mapping(self):
        return {
            API_GATEWAY_TYPE: self._get_api_gateway_link
        }

    def create_update_swagger_ui(self, args):
        return self.create_pool(self._create_update_swagger_ui_from_meta, args)

    def remove_swagger_ui(self, args):
        return self.create_pool(self._remove_swagger_ui, args)

    @unpack_kwargs
    def _create_update_swagger_ui_from_meta(self, name, meta, context=None):
        artifact_dir = PurePath(self.conf_path, ARTIFACTS_FOLDER,
                                name).as_posix()
        target_bucket = meta.get('target_bucket')
        if not target_bucket:
            raise ParameterError(
                f'Target bucket for Swagger UI \'{name}\' is absent in '
                f'resource meta'
            )
        if not self.s3_conn.is_bucket_exists(target_bucket):
            raise ResourceNotFoundError(
                f'Target bucket \'{target_bucket}\' for Swagger UI \'{name}\' '
                f'doesn\'t exists'
            )
        artifact_path = meta.get(S3_PATH_NAME)
        if not artifact_path:
            raise ParameterError(f'Can\'t resolve Swagger UI artifact path')
        artifact_src_path = posixpath.join(
            self.deploy_target_bucket_key_compound, artifact_path)

        _LOG.info(f'Downloading an artifact for Swagger UI \'{name}\'')
        with io.BytesIO() as artifact:
            self.s3_conn.download_to_file(
                bucket_name=self.deploy_target_bucket,
                key=artifact_src_path,
                file=artifact)
            extract_to = build_path(artifact_dir, name)
            with ZipFile(artifact, 'r') as zf:
                zf.extractall(extract_to)

        _LOG.info(f'Uploading files for Swagger UI \'{name}\' to target '
                  f'bucket \'{target_bucket}\'')
        for file in os.listdir(extract_to):
            extra_args = None
            if file == INDEX_FILE_NAME:
                extra_args = {
                    'ContentType': 'text/html',
                    'ContentDisposition': f'inline;filename={INDEX_FILE_NAME}'
                }
            elif file.endswith('.json'):
                filepath = PurePath(extract_to, file)
                self.resolve_api_url(filepath, meta)

            self.s3_conn.upload_single_file(path=PurePath(extract_to,
                                                          file).as_posix(),
                                            key=file,
                                            bucket=target_bucket,
                                            extra_args=extra_args)

        _LOG.info(f'Removing temporary directory \'{artifact_dir}\'')
        rmtree(artifact_dir)

        return self.describe_swagger_ui(name, meta)

    def describe_swagger_ui(self, name, meta):
        target_bucket = meta.get('target_bucket')
        arn = (f'arn:aws-syndicate:{self.region}:{self.account_id}:'
               f'{name}')
        spec_file_name = SWAGGER_UI_SPEC_NAME_TEMPLATE.format(
            name=name)
        website_hosting = self.s3_conn.get_bucket_website(target_bucket)
        bucket_description = {
            'arn': f'arn:aws:s3:::{target_bucket}',
            'bucket_acl': self.s3_conn.get_bucket_acl(target_bucket),
            'location': self.s3_conn.get_bucket_location(target_bucket),
            'policy': self.s3_conn.get_bucket_policy(target_bucket)
        }
        if not bucket_description['location']:
            return {}
        response = {
            'host_description': bucket_description
        }
        if website_hosting:
            hosting_config = {
                "enabled": True,
                "index_document": deep_get(website_hosting,
                                           ['IndexDocument', 'Suffix'])
            }
            if self.s3_conn.is_file_exists(target_bucket, spec_file_name):
                hosting_config['api_spec_document'] = spec_file_name
            hosting_config['endpoint'] = (
                S3_LINK_TEMPLATE.format(target_bucket=target_bucket,
                                        region=self.region)
            )
            response['website_hosting'] = hosting_config
        return {
            arn: build_description_obj(response, name, meta)
        }

    @unpack_kwargs
    def _remove_swagger_ui(self, arn, config) -> dict:
        resource_name = arn.split(':')[-1]
        target_bucket = deep_get(config, ['resource_meta', 'target_bucket'])

        pure_name = resource_name
        if self.extended_prefix_mode:
            if self.prefix:
                pure_name = pure_name[len(self.prefix):]
            if self.suffix:
                pure_name = pure_name[:-len(self.suffix)]

        if not self.s3_conn.is_bucket_exists(target_bucket):
            USER_LOG.info(f'Target bucket with name \'{target_bucket}\' not '
                          f'found')
            return {arn: config}
        else:
            self.s3_conn.remove_object(bucket_name=target_bucket,
                                       file_name=INDEX_FILE_NAME)
            self.s3_conn.remove_object(
                bucket_name=target_bucket,
                file_name=SWAGGER_UI_SPEC_NAME_TEMPLATE.format(
                    name=pure_name))
            USER_LOG.info(f'Swagger UI \'{resource_name}\' removed')
            return {arn: config}

    @staticmethod
    def validate_server_params(server_params: dict) -> bool:
        required = [RESOURCE_TYPE_PARAM,
                    RESOURCE_NAME_PARAM,
                    PARAMETER_NAME_PARAM,
                    PARAMETER_TYPE_PARAM]

        if not set(server_params).issubset(set(required)):
            _LOG.error(f'Incorrect values in `{X_SYNDICATE_SERVER_PARAM}` '
                       f'parameter. Must be a subset of these: {required}')
            USER_LOG.warn('Cannot retrieve active URL for swagger UI')
            return False
        return True

    def _get_api_gateway_link(self, server_params: dict, meta: dict) -> \
            Optional[str]:
        resource_name = server_params.get(RESOURCE_NAME_PARAM)
        if self.extended_prefix_mode:
            if self.prefix:
                resource_name = self.prefix + resource_name
            if self.suffix:
                resource_name = resource_name + self.suffix
        stage_name = server_params.get(PARAMETER_NAME_PARAM)

        response = self.resources_provider.api_gw().\
            describe_api_resources(name=resource_name, meta=meta)
        if not response:
            _LOG.warning(
                f'Cannot find `{resource_name}` API Gateway. Cannot retrieve '
                f'active URL for swagger UI')
            return

        first_value = next(iter(response.values()))
        api_url = API_LINK_TEMPLATE.format(
            api_id=first_value['description']['id'],
            region=self.region,
            stage_name=stage_name
        )
        return api_url

    def resolve_api_url(self, filepath: str | PurePath, meta: dict) -> None:
        try:
            with open(filepath, 'r') as f:
                file_content = json.load(f)

            server_params = file_content.get(X_SYNDICATE_SERVER_PARAM)
            _LOG.debug(f'x-syndicate-server parameters: {server_params}')
            if not server_params or \
                    not self.validate_server_params(server_params):
                return

            resource_type = server_params.get(RESOURCE_TYPE_PARAM)
            api_func = self.server_api_mapping.get(resource_type)

            if not api_func:
                _LOG.warning(
                    f'The resource type \'{resource_type}\' is not supported '
                    f'for \'{X_SYNDICATE_SERVER_PARAM}\' configuration.')
                return

            api_url = api_func(server_params, meta)
            if not api_url:
                return

            file_content['servers'][0]['url'] = api_url
            with open(filepath, 'w') as f:
                json.dump(file_content, f)
        except (FileNotFoundError, KeyError, AttributeError,
                json.JSONDecodeError) as e:
            _LOG.error(f'Error processing file {filepath}: {str(e)}')
