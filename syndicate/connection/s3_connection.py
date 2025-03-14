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
from json import dumps

from boto3 import resource
from botocore.client import Config
from botocore.exceptions import ClientError

from syndicate.commons import deep_get
from syndicate.exceptions import InvalidValueError
from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger(__name__)


@apply_methods_decorator(retry())
class S3Connection(object):
    """ S3 connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.resource = resource('s3', self.region,
                                 config=Config(signature_version='s3v4'),
                                 aws_access_key_id=self.aws_access_key_id,
                                 aws_secret_access_key=self.aws_secret_access_key,
                                 aws_session_token=self.aws_session_token)
        self.client = self.resource.meta.client
        _LOG.debug('Opened new S3 connection.')

    def load_file_body(self, bucket_name, key):
        return self.resource.Object(bucket_name, key).get()['Body'].read()

    def download_file(self, bucket_name, key, file_path):
        self.resource.Bucket(bucket_name).download_file(key, file_path)

    def download_to_file(self, bucket_name, key, file):
        self.resource.Bucket(bucket_name).download_fileobj(key, file)

    def upload_file(self, storage, file_name, bucket_name, folder=''):
        """ Upload specific file to s3.

        :type bucket_name: str
        :type file_name: str
        :type storage: str
        :param storage: path (e.g. '/tmp/')
        :param folder: str
        """
        self.client.upload_file(storage + file_name, bucket_name,
                                folder + file_name)

    def upload_single_file(self, path, key, bucket, extra_args=None):
        """ Uploads file just like method above, but allows to specify
        object key as argument

        :param path: path to actual file on os
        :param key: object key, as it will be uploaded to bucket
        :param bucket: just bucket name
        :param extra_args: Extra arguments that may be passed to the client
        operation
        """
        self.client.upload_file(path, bucket, key, ExtraArgs=extra_args)

    def put_object(self, file_obj, key, bucket,
                   content_type, content_encoding=None):
        if content_encoding is None:
            self.resource.Bucket(bucket).put_object(Body=file_obj,
                                                    ContentType=content_type,
                                                    Key=key)
        else:
            self.resource.Bucket(bucket).put_object(
                Body=file_obj,
                ContentType=content_type,
                Key=key,
                ContentEncoding=content_encoding)

    def is_bucket_exists(self, name):
        """ Check if bucket exists by name.

        :type name: str
        """
        res = self.get_list_buckets()
        existing_buckets = [each['Name'] for each in res]
        return name in existing_buckets

    def get_bucket_acl(self, bucket_name):
        try:
            return self.client.get_bucket_acl(Bucket=bucket_name)
        except ClientError as e:
            if 'NoSuchBucket' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_bucket_location(self, bucket_name):
        try:
            return self.client.get_bucket_location(Bucket=bucket_name)
        except ClientError as e:
            if 'NoSuchBucket' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_bucket_policy(self, bucket_name):
        try:
            return self.client.get_bucket_policy(Bucket=bucket_name)
        except ClientError as e:
            if 'NoSuchBucketPolicy' or 'NoSuchBucket' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_bucket_website(self, bucket_name):
        try:
            return self.client.get_bucket_website(Bucket=bucket_name)
        except ClientError as e:
            if 'NoSuchWebsiteConfiguration' or 'NoSuchBucket' in str(e):
                pass  # valid exception
            else:
                raise e

    def is_file_exists(self, bucket_name, key):
        """ Check if file exists.

        :type bucket_name: str
        :type key: str
        """
        return True if self.retrieve_object_metadata(bucket_name, key) else \
            False

    def create_bucket(self, bucket_name, acl=None, location=None):
        """
        :type bucket_name: str
        :param acl: private|public-read|public-read-write|authenticated-read
        :param location: region
        """
        param = dict(Bucket=bucket_name)
        param['ObjectOwnership'] = 'ObjectWriter'
        if acl:
            param['ACL'] = acl
        if not location:
            location = self.region
        valid_location = ['us-west-1', 'us-west-2', 'ca-central-1',
                          'eu-west-1', 'eu-west-2', 'eu-west-3',
                          'eu-central-1',
                          'ap-south-1', 'ap-southeast-1', 'ap-southeast-2',
                          'ap-northeast-1', 'ap-northeast-2', 'sa-east-1',
                          'us-east-2', 'eu-central-1', 'us-east-1',
                          'eu-north-1']
        if location not in valid_location:
            raise InvalidValueError(
                f"Param 'location' has invalid value. Valid locations: "
                f"'{valid_location}'"
            )
        if location != 'us-east-1':  # this is default location
            param['CreateBucketConfiguration'] = {
                'LocationConstraint': location
            }
        self.client.create_bucket(**param)

    def remove_bucket(self, bucket_name, log_not_found_error=True):
        """ Remove bucket by name. To remove bucket it must be empty.
        log_not_found_error parameter is needed for proper log handling in the
        retry decorator
        """
        bucket = self.resource.Bucket(bucket_name)
        bucket_versioning = self.resource.BucketVersioning(bucket_name)
        if bucket_versioning.status == 'Enabled':
            bucket.object_versions.delete()
        else:
            bucket.objects.all().delete()
        bucket.delete()

    def delete_bucket(self, bucket_name):
        self.client.delete_bucket(Bucket=bucket_name)

    def add_lambda_event_source(self, bucket: str, lambda_arn: str,
                                event_source: dict):
        """ Create event notification in the bucket that triggers the lambda
        Note: two identical events can't be configured for two
        separate lambdas in one bucket

        :param bucket:
        :param lambda_arn:
        :param event_source:
            - s3_events: list[str] - list of S3 event types:
                's3:ReducedRedundancyLostObject'
                's3:ObjectCreated:*'
                's3:ObjectCreated:Put'
                's3:ObjectCreated:Post'
                's3:ObjectCreated:Copy'
                's3:ObjectCreated:CompleteMultipartUpload'
                's3:ObjectRemoved:*'
                's3:ObjectRemoved:Delete'
                's3:ObjectRemoved:DeleteMarkerCreated'
            - filter_rules (optional): list[dict] - list of S3 event filters:
                {'Name': 'prefix'|'suffix', 'Value': 'string'}
        """
        config = self.get_bucket_notification(bucket_name=bucket)
        config.pop('ResponseMetadata')

        if 'LambdaFunctionConfigurations' not in config:
            config['LambdaFunctionConfigurations'] = []

        # for some reason filter rule's name value is in uppercase when
        # should be in lower according to the documentation
        for lambda_config in config['LambdaFunctionConfigurations']:
            filter_rules = deep_get(
                lambda_config, ['Filter', 'Key', 'FilterRules'], [])
            for filter_rule in filter_rules:
                filter_rule['Name'] = filter_rule['Name'].lower()

        params = {
            'LambdaFunctionArn': lambda_arn,
            'Events': event_source['s3_events']
        }
        if event_source.get('filter_rules'):
            params.update({
                'Filter': {
                    'Key': {
                        'FilterRules': event_source['filter_rules']
                    }
                }
            })
        # add event notification to remote if it is not already present
        for remote_event_source in config['LambdaFunctionConfigurations']:
            remote_event_source_copy = remote_event_source.copy()
            remote_event_source_copy.pop('Id')
            if remote_event_source_copy == params:
                break
        else:
            config['LambdaFunctionConfigurations'].append(params)

        self.put_bucket_notification(
            bucket_name=bucket, notification_configuration=config)

    def remove_lambda_event_source(self, bucket: str, lambda_arn: str,
                                   event_source: dict):
        """ Remove event notification in the bucket that triggers the lambda
        Note: two identical events can't be configured for two
        separate lambdas in one bucket

        :param bucket:
        :param lambda_arn:
        :param event_source:
            - s3_events: list[str] - list of S3 event types:
                's3:ReducedRedundancyLostObject'
                's3:ObjectCreated:*'
                's3:ObjectCreated:Put'
                's3:ObjectCreated:Post'
                's3:ObjectCreated:Copy'
                's3:ObjectCreated:CompleteMultipartUpload'
                's3:ObjectRemoved:*'
                's3:ObjectRemoved:Delete'
                's3:ObjectRemoved:DeleteMarkerCreated'
            - filter_rules (optional): list[dict] - list of S3 event filters:
                {'Name': 'prefix'|'suffix', 'Value': 'string'}
        """
        config = self.get_bucket_notification(bucket_name=bucket)
        config.pop('ResponseMetadata')

        if 'LambdaFunctionConfigurations' not in config:
            _LOG.info('No lambda event source to remove')
            return

        saved_lambda_configs = []
        for lambda_config in config['LambdaFunctionConfigurations']:
            # for some reason filter rule's name value is in uppercase when
            # should be in lower according to the documentation
            filter_rules = deep_get(
                lambda_config, ['Filter', 'Key', 'FilterRules'], [])
            for filter_rule in filter_rules:
                filter_rule['Name'] = filter_rule['Name'].lower()

            current_lambda = (lambda_config['LambdaFunctionArn'] == lambda_arn)
            same_filters = filter_rules == event_source.get('filter_rules', [])
            same_events = lambda_config['Events'] == event_source['s3_events']
            # save config if something is different from current meta
            if not current_lambda or not same_filters or not same_events:
                saved_lambda_configs.append(lambda_config)

        config['LambdaFunctionConfigurations'] = saved_lambda_configs
        self.put_bucket_notification(
            bucket_name=bucket, notification_configuration=config)

    def get_list_buckets(self):
        response = self.client.list_buckets()
        return response.get('Buckets')

    def add_bucket_policy(self, bucket_name, policy_document):
        """ Attach inline policy to existing bucket.

        :type bucket_name: str
        :type policy_document: str (json)
        """
        if isinstance(policy_document, dict):
            policy_document = dumps(policy_document)
        self.client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=policy_document
        )

    def add_bucket_rule(self, bucket_name, rule_document):
        """
        Creates rule to existing bucket.

        :param bucket_name:
        :param rule_document:
        :return:
        """
        self.client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=rule_document
        )

    def enable_website_hosting(self, bucket, index_doc, error_doc):
        """
        :type bucket: str
        :type index_doc: str
        :type error_doc: str
        """
        self.client.put_bucket_website(
            Bucket=bucket,
            WebsiteConfiguration={
                'ErrorDocument': {
                    'Key': error_doc
                },
                'IndexDocument': {
                    'Suffix': index_doc
                }
            }
        )

    def remove_object(self, bucket_name, file_name, mfa=None, version_id=None,
                      request_payer=None):
        """
        :type bucket_name: str
        :type file_name: str
        :type mfa: str
        :type version_id: str
        :type request_payer: str
        :return: response (dict)
        """
        params = dict(Bucket=bucket_name, Key=file_name)
        if mfa:
            params['MFA'] = mfa
        if version_id:
            params['VersionId'] = version_id
        if request_payer:
            params['RequestPayer'] = request_payer
        return self.client.delete_object(**params)

    def list_objects(self, bucket_name, delimiter=None, encoding_type=None,
                     prefix=None, request_payer=None):
        params = dict(Bucket=bucket_name)
        if delimiter:
            params['Delimiter'] = delimiter
        if encoding_type:
            params['EncodingType'] = encoding_type
        if prefix:
            params['Prefix'] = prefix
        if request_payer:
            params['RequestPayer'] = request_payer

        bucket_objects = []
        response = self.client.list_objects(**params)
        marker = response.get('Marker')
        if response.get('Contents'):
            bucket_objects.extend(response.get('Contents'))
        while marker:
            params['Marker'] = marker
            response = self.client.list_objects(**params)
            marker = response.get('Marker')
            if response.get('Contents'):
                bucket_objects.extend(response.get('Contents'))
        return bucket_objects

    def get_bucket_notification(self, bucket_name):
        try:
            return self.client.get_bucket_notification_configuration(
                Bucket=bucket_name
            )
        except ClientError as e:
            if 'AccessDenied' in str(e):
                _LOG.warning(f'{e}. Bucket name - \'{bucket_name}\'.')
            else:
                raise e

    def put_bucket_notification(self, bucket_name, notification_configuration):
        self.client.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration=notification_configuration
        )

    def remove_bucket_notification(self, bucket_name):
        self.client.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration={}
        )

    def list_keys(self, bucket_name):
        bucket = self.resource.Bucket(bucket_name)
        result = [obj.key for obj in bucket.objects.all()]
        return result

    def get_keys_by_prefix(self, bucket_name, prefix):
        bucket = self.resource.Bucket(bucket_name)
        return [obj.key for obj in bucket.objects.filter(Prefix=prefix)]

    def list_object_versions(self, bucket_name, delimeter=None,
                             encoding_type=None, prefix=None):
        params = dict(Bucket=bucket_name)
        if delimeter:
            params['Delimiter'] = delimeter
        if encoding_type:
            params['EncodingType'] = encoding_type
        if prefix:
            params['Prefix'] = prefix

        bucket_objects = []
        response = self.client.list_object_versions(**params)
        versions = response.get('Versions', [])
        bucket_objects.extend(
            [{
                'Key': i['Key'],
                'VersionId': i['VersionId']
            } for i in versions])
        key_marker = response.get('NextKeyMarker')
        version_marker = response.get('NextVersionIdMarker')
        while key_marker or version_marker:
            if key_marker:
                params['KeyMarker'] = key_marker
            if version_marker:
                params['VersionIdMarker'] = version_marker
            response = self.client.list_object_versions(**params)
            versions = response.get('Versions', [])
            bucket_objects.extend(
                [{
                    'Key': i['Key'],
                    'VersionId': i['VersionId']
                } for i in versions])
        return bucket_objects

    def list_object_markers(self, bucket_name, delimeter=None,
                            encoding_type=None, prefix=None):
        params = dict(Bucket=bucket_name)
        if delimeter:
            params['Delimiter'] = delimeter
        if encoding_type:
            params['EncodingType'] = encoding_type
        if prefix:
            params['Prefix'] = prefix

        bucket_objects = []
        response = self.client.list_object_versions(**params)
        delete_markers = response.get('DeleteMarkers', [])
        bucket_objects.extend(
            [{
                'Key': i['Key'],
                'VersionId': i['VersionId']
            } for i in delete_markers])
        key_marker = response.get('NextKeyMarker')
        version_marker = response.get('NextVersionIdMarker')
        while key_marker or version_marker:
            if key_marker:
                params['KeyMarker'] = key_marker
            if version_marker:
                params['VersionIdMarker'] = version_marker
            response = self.client.list_object_versions(**params)
            delete_markers = response.get('DeleteMarkers', [])
            bucket_objects.extend(
                [{
                    'Key': i['Key'],
                    'VersionId': i['VersionId']
                } for i in delete_markers])
        return bucket_objects

    def retrieve_object_metadata(self, bucket_name, key):
        try:
            return self.client.head_object(Bucket=bucket_name, Key=key)
        except ClientError as e:
            if 'HeadObject' in str(e):
                pass  # valid exception
            else:
                raise e
            return

    def delete_objects(self, bucket_name, objects, mfa=None,
                       request_payer=None):
        params = dict(Bucket=bucket_name, Delete={'Objects': objects})
        if mfa:
            params['MFA'] = mfa
        if request_payer:
            params['RequestPayer'] = request_payer
        return self.client.delete_objects(**params)

    def put_cors(self, bucket_name, rules):
        """
        Puts buckets configuration for existing bucket.
        :param bucket_name: name of the bucket.
        :param rules: list of rules. Each rule may have
            the following attributes: AllowedHeaders, AllowedMethods,
            AllowedOrigins, ExposeHeaders, MaxAgeSeconds;
        :return: None as boto3 does.
        """

        boto_rules = []
        for rule in rules:
            # converting rule to boto format
            for key in rule.keys():
                if isinstance(rule[key], list) \
                        or isinstance(rule[key], int):
                    pass  # expected
                elif isinstance(rule[key], str):
                    rule[key] = [rule[key]]
                else:
                    raise InvalidValueError(
                        f"Value of CORS rule attribute '{key}' has invalid "
                        f"value: '{rule[key]}'. Should be str, int or list"
                    )
            boto_rules.append(rule)

        # boto3 returns None here
        self.client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": boto_rules
            }
        )
        _LOG.info('CORS configuration has been set to bucket {0}'.format(
            bucket_name))

    def is_versioning_enabled(self, bucket_name):
        return self.client.get_bucket_versioning(
            Bucket=bucket_name) == 'Enabled'

    def put_public_access_block(self, bucket_name: str,
                                block_public_acls: bool = True,
                                ignore_public_acls: bool = True,
                                block_public_policy: bool = True,
                                restrict_public_buckets: bool = True):
        public_access_block_configuration = {
            'BlockPublicAcls': block_public_acls,
            'IgnorePublicAcls': ignore_public_acls,
            'BlockPublicPolicy': block_public_policy,
            'RestrictPublicBuckets': restrict_public_buckets
        }
        _LOG.info(f'Setting public access block for bucket: {bucket_name} '
                  f'with params: {public_access_block_configuration}')
        self.client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration=public_access_block_configuration
        )
        _LOG.info(f'Public access block was set')

    def put_bucket_acl(self, bucket_name: str, acl: str):
        self.client.put_bucket_acl(
            Bucket=bucket_name,
            ACL=acl
        )
        _LOG.info(f'ACL was set as \'{acl}\'')
