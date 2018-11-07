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
from syndicate.core import CONN, ClientError
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.helper import build_description_obj, chunks

_LOG = get_logger('syndicate.core.resources.s3_resource')
_S3_CONN = CONN.s3()


def create_s3_bucket(args):
    return create_pool(_create_s3_bucket_from_meta, args, 5)


def describe_bucket(name, meta):
    arn = 'arn:aws:s3:::{0}'.format(name)
    acl_response = _S3_CONN.get_bucket_acl(name)
    location_response = _S3_CONN.get_bucket_location(name)
    bucket_policy = _S3_CONN.get_bucket_policy(name)
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
def _create_s3_bucket_from_meta(name, meta):
    if _S3_CONN.is_bucket_exists(name):
        _LOG.warn('{0} bucket exists.'.format(name))
        return describe_bucket(name, meta)
    _S3_CONN.create_bucket(name, meta.get('acl'), meta.get('location'))
    policy = meta.get('policy')
    if policy:
        _S3_CONN.add_bucket_policy(name, policy)
        _LOG.debug('Policy on {0} S3 bucket is set up.'.format(name))
    _LOG.info('Created S3 bucket {0}.'.format(name))
    rules = meta.get('LifecycleConfiguration')
    if rules:
        _S3_CONN.add_bucket_rule(name, rules)
        _LOG.debug('Rules on {0} S3 bucket are set up.'.format(name))
    return describe_bucket(name, meta)


def _delete_objects(bucket_name, keys):
    response = _S3_CONN.delete_objects(bucket_name, keys)
    errors = response.get('Errors')
    if errors:
        error_keys = [{
                          'Key': i['Key'],
                          'VersionId': i['VersionId']
                      } for i in errors]
        return error_keys
    else:
        return []


def remove_buckets(args):
    create_pool(_remove_bucket, args, 5)


@unpack_kwargs
def _remove_bucket(arn, config):
    bucket_name = config['resource_name']
    try:
        errors = []
        keys = _S3_CONN.list_object_versions(bucket_name)
        if keys:
            for s3_keys in chunks(keys, 1000):
                errors.extend(_delete_objects(bucket_name, s3_keys))

        markers = _S3_CONN.list_object_markers(bucket_name)
        if markers:
            for s3_markers in chunks(markers, 1000):
                errors.extend(_delete_objects(bucket_name, s3_markers))

        if errors:
            raise AssertionError('Error occurred while deleting S3 objects'
                                 ' from {0} bucket. Not deleted keys: '
                                 '{1}'.format(bucket_name, str(errors)))
        else:
            _S3_CONN.delete_bucket(bucket_name)
            _LOG.info('S3 bucket {0} was removed.'.format(bucket_name))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            _LOG.warn('S3 bucket {0} is not found'.format(bucket_name))
        else:
            raise e
