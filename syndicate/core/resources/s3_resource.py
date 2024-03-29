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
import ipaddress
import re
import string
from typing import Optional

from syndicate.commons.log_helper import get_logger, get_user_logger
from syndicate.core import ClientError
from syndicate.core.constants import S3_BUCKET_ACL_LIST
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, chunks

_LOG = get_logger('syndicate.core.resources.s3_resource')
USER_LOG = get_user_logger()


def validate_bucket_name(bucket_name: str):
    """Checks whether the given bucket name is valid.
    If the given name isn't valid, ValueError with an appropriate message
    is raised.
    :type bucket_name: str
    :param bucket_name: the name to check
    """
    bucket_name = bucket_name.strip()
    _LOG.info(f"Starting validating bucket name '{bucket_name}'")
    error = None

    raw_bucket_name, _ = (bucket_name.split('/', 1)
                          if bucket_name and '/' in bucket_name
                          else (bucket_name, None))
    if not raw_bucket_name or not 3 <= len(raw_bucket_name) <= 63:
        error = 'Bucket name must be between 3 and 63 characters long'
    else:
        invalid_characters = re.search('[^a-z0-9.-]', bucket_name)
        if invalid_characters:
            character = invalid_characters.group()
            if character in string.ascii_uppercase:
                error = 'Bucket name must not contain uppercase characters'
            else:
                error = f'Bucket name contains invalid characters: {character}'
        elif any(bucket_name.startswith(symbol) for symbol in '.-'):
            error = 'Bucket name must start with a lowercase letter or number'
        elif any(bucket_name.endswith(symbol) for symbol in '.-'):
            error = 'Bucket name must not end with dash or period'
        elif '..' in bucket_name:
            error = 'Bucket name must not contain two adjacent periods'
        elif '.-' in bucket_name or '-.' in bucket_name:
            error = 'Bucket name must not contain dash next to period'
        else:
            try:
                ipaddress.ip_address(bucket_name)
                error = 'Bucket name must not resemble an IP address'
            except ValueError:
                pass
    if error:
        _LOG.warning(error)
        raise ValueError(error)
    _LOG.info(f"Finished validating bucket name '{bucket_name}'")


class S3Resource(BaseResource):

    def __init__(self, s3_conn, account_id) -> None:
        self.s3_conn = s3_conn
        self.account_id = account_id

    def create_s3_bucket(self, args):
        return self.create_pool(self._create_s3_bucket_from_meta, args)

    def describe_bucket(self, name, meta):
        arn = self.get_bucket_arn(name)
        acl_response = self.s3_conn.get_bucket_acl(name)
        location_response = self.s3_conn.get_bucket_location(name)
        bucket_policy = self.s3_conn.get_bucket_policy(name)
        response = {
            'bucket_acl': acl_response,
            'location': location_response,
        }
        if bucket_policy:
            response['policy'] = bucket_policy
        return {
            arn: build_description_obj(response, name, meta)
        }

    @staticmethod
    def get_bucket_arn(name):
        return 'arn:aws:s3:::{0}'.format(name)

    @unpack_kwargs
    def _create_s3_bucket_from_meta(self, name, meta):
        if self.s3_conn.is_bucket_exists(name):
            _LOG.warn('{0} bucket exists.'.format(name))
            return self.describe_bucket(name, meta)

        self.s3_conn.create_bucket(name, location=meta.get('location'))
        _LOG.info('Created S3 bucket {0}.'.format(name))

        public_access_block = meta.get('public_access_block', {})
        if not all([isinstance(param, bool) for param in
                    public_access_block.values()]):
            message = f'Parameters inside public_access_block should have ' \
                      f'bool type'
            _LOG.error(message)
            raise AssertionError(message)
        self.s3_conn.put_public_access_block(name,
                                             **public_access_block)

        acl = meta.get('acl')
        if acl:
            if acl not in S3_BUCKET_ACL_LIST:
                raise AssertionError(
                    f'Invalid value of S3 bucket ACL! Must be one of the '
                    f'{S3_BUCKET_ACL_LIST}')
            self.s3_conn.put_bucket_acl(name, acl)

        policy = meta.get('policy')
        if policy:
            self._populate_bucket_name_in_policy(policy, name)
            self.s3_conn.add_bucket_policy(name, policy)
            _LOG.debug('Policy on {0} S3 bucket is set up.'.format(name))

        website_hosting = meta['website_hosting'].get('enabled') \
            if meta.get('website_hosting') else None
        if website_hosting:
            index_document = meta['website_hosting'].get('index_document')
            error_document = meta['website_hosting'].get('error_document')
            if not all([isinstance(param, str) for param in (index_document,
                                                             error_document)]):
                raise AssertionError('Parameters \'index_document\' and '
                                     '\'error_document\' must be \'str\' type')
            self.s3_conn.enable_website_hosting(name,
                                                index_document,
                                                error_document)
            _LOG.debug(f'Website hosting configured with parameters: '
                       f'\'index_document\': \'{index_document}\', '
                       f'\'error_document\': \'{error_document}\'')
            website_endpoint = (
                f'http://{name}.s3-website.{self.s3_conn.region}.amazonaws.com'
                f'/{index_document}')
            USER_LOG.info(f'Bucket website endpoint: {website_endpoint}')

        rules = meta.get('LifecycleConfiguration')
        if rules:
            self.s3_conn.add_bucket_rule(name, rules)
            _LOG.debug('Rules on {0} S3 bucket are set up.'.format(name))

        cors_configuration = meta.get('cors')
        if cors_configuration:
            self.s3_conn.put_cors(bucket_name=name, rules=cors_configuration)
        return self.describe_bucket(name, meta)

    def _delete_objects(self, bucket_name, keys):
        response = self.s3_conn.delete_objects(bucket_name, keys)
        errors = response.get('Errors')
        if errors:
            error_keys = [{
                'Key': i['Key'],
                'VersionId': i['VersionId']
            } for i in errors]
            return error_keys
        else:
            return []

    def remove_buckets(self, args):
        self.create_pool(self._remove_bucket, args)

    @unpack_kwargs
    def _remove_bucket(self, arn, config):
        bucket_name = config['resource_name']
        try:
            errors = []
            keys = self.s3_conn.list_object_versions(bucket_name)
            if keys:
                for s3_keys in chunks(keys, 1000):
                    errors.extend(self._delete_objects(bucket_name, s3_keys))

            markers = self.s3_conn.list_object_markers(bucket_name)
            if markers:
                for s3_markers in chunks(markers, 1000):
                    errors.extend(
                        self._delete_objects(bucket_name, s3_markers))

            if errors:
                raise AssertionError('Error occurred while deleting S3 objects'
                                     ' from {0} bucket. Not deleted keys: '
                                     '{1}'.format(bucket_name, str(errors)))
            else:
                self.s3_conn.delete_bucket(bucket_name)
                _LOG.info('S3 bucket {0} was removed.'.format(bucket_name))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                _LOG.warn('S3 bucket {0} is not found'.format(bucket_name))
            else:
                raise e

    def build_bucket_arn(self, maybe_arn: str) -> Optional[str]:
        if not isinstance(maybe_arn, str):
            return
        if self.is_bucket_arn(maybe_arn):
            return maybe_arn
        return f'arn:aws:s3:::{maybe_arn}'

    @staticmethod
    def is_bucket_arn(maybe_arn: str) -> bool:
        # TODO add files keys support to regex
        return bool(re.match(r'^arn:aws:s3:::[a-z0-9.-]{3,63}/?$',
                             maybe_arn))

    @staticmethod
    def _populate_bucket_name_in_policy(policy, bucket_name):
        statements = policy['Statement'] if policy.get('Statement') else []
        for statement in statements:
            resources = statement['Resource'] if statement.get('Resource') \
                else []
            new_resources = []
            for resource in resources:
                if 'bucket_name' in resource:
                    new_resources.append(resource.format(bucket_name=
                                                         bucket_name))
                else:
                    new_resources.append(resource)
            statement['Resource'] = new_resources
