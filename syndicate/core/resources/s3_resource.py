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
from string import whitespace

from syndicate.commons.log_helper import get_logger
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, chunks

_LOG = get_logger('syndicate.core.resources.s3_resource')


def validate_bucket_name(bucket_name: str):
    """Checks whether the given bucket name is compliant. The function was
    built based on the same one from aws-sdk-java.
    It's expected to work pretty fast.
    If the given name isn't valid, ValueError with an appropriate message
    is raised.

    :type bucket_name: str
    :param bucket_name: the name to check
    """
    bucket_name = bucket_name.strip()

    _LOG.info(f"Starting validating bucket name '{bucket_name}'")
    try:
        if not 3 <= len(bucket_name) <= 63:
            raise ValueError(f"Bucket name '{bucket_name}' length is "
                             f"{len(bucket_name)}, but must be between "
                             f"3 and 63")

        is_ip = False
        try:
            ipaddress.ip_address(bucket_name)
            is_ip = True
        except ValueError:
            _LOG.info(f"Bucket name '{bucket_name}' isn't like ip address "
                      f"and has a valid length")
        if is_ip:
            raise ValueError(f"Bucket name '{bucket_name}' cannot be "
                             f"ip address-like")

        previous = '\0'

        for char in bucket_name:
            ascii = ord(char)
            if char.isupper():
                raise ValueError(f"Bucket name '{bucket_name}' "
                                 f"cannot contain uppercase letters")
            if char in whitespace:
                raise ValueError(f"Bucket name '{bucket_name}' "
                                 f"cannot contain whitespaces")
            if char == '.':
                if previous == '\0':
                    raise ValueError(f"Bucket name '{bucket_name}' "
                                     f"cannot start with '.'")
                if previous == '.':
                    raise ValueError(f"Bucket name '{bucket_name}' "
                                     f"cannot contain '..'")
                if previous == '-':
                    raise ValueError(f"Bucket name '{bucket_name}' "
                                     f"cannot contain a dash before a dot")
            elif char == '-':
                if previous == '.':
                    raise ValueError(f"Bucket name '{bucket_name}' "
                                     f"cannot contain a dot before a dash")
                if previous == '\0':
                    raise ValueError(f"Bucket name '{bucket_name}' "
                                     f"cannot start with '-'")
            elif ascii < ord('0') or ord('9') < ascii < ord(
                    'a') or ascii > ord(
                    'z'):
                raise ValueError(
                    f"Bucket name '{bucket_name}' cannot contain '{char}'")

            previous = char

        if previous == '-' or previous == '.':
            raise ValueError(
                f"Bucket name '{bucket_name}' cannot end with '.' or '-'")
    except ValueError as e:
        _LOG.info(e.__str__())
        raise e

    _LOG.info(f"Finishing validating bucket '{bucket_name}'")

class S3Resource(BaseResource):

    def __init__(self, s3_conn) -> None:
        self.s3_conn = s3_conn

    def create_s3_bucket(self, args):
        return self.create_pool(self._create_s3_bucket_from_meta, args)

    def describe_bucket(self, name, meta):
        arn = 'arn:aws:s3:::{0}'.format(name)
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

    @unpack_kwargs
    def _create_s3_bucket_from_meta(self, name, meta):
        if self.s3_conn.is_bucket_exists(name):
            _LOG.warn('{0} bucket exists.'.format(name))
            return self.describe_bucket(name, meta)
        self.s3_conn.create_bucket(name, meta.get('acl'), meta.get('location'))
        policy = meta.get('policy')
        if policy:
            self.s3_conn.add_bucket_policy(name, policy)
            _LOG.debug('Policy on {0} S3 bucket is set up.'.format(name))
        _LOG.info('Created S3 bucket {0}.'.format(name))
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

