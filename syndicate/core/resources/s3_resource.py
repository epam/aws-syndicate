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
from syndicate.commons.log_helper import get_logger
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, chunks

_LOG = get_logger('syndicate.core.resources.s3_resource')


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
