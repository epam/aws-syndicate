"""
    Copyright 2021 EPAM Systems, Inc.

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
from troposphere import s3, Ref

from .cf_resource_converter import CfResourceConverter
from ..cf_transform_helper import to_logic_name


CANNED_ACL_PARAMS_MAPPING = {
    'private': s3.Private,
    'public-read': s3.PublicRead,
    'public-read-write': s3.PublicReadWrite,
    'aws-exec-read': 'AwsExecRead',
    'authenticated-read': s3.AuthenticatedRead,
    'bucket-owner-read': s3.BucketOwnerRead,
    'bucket-owner-full-control': s3.BucketOwnerFullControl,
    'log-delivery-write': s3.LogDeliveryWrite,
}


class CfS3Converter(CfResourceConverter):

    def convert(self, name, meta):
        bucket = s3.Bucket(to_logic_name(name))
        bucket.BucketName = name
        self.template.add_resource(bucket)

        # location = meta.get('location')
        #   Ignore location as CloudFormation creates an Amazon S3 bucket in
        #   the same AWS Region where you create the AWS CloudFormation stack.

        acl = meta.get('acl')
        if acl:
            bucket.AccessControl = CANNED_ACL_PARAMS_MAPPING[acl]

        policy = meta.get('policy')
        if policy:
            bucket_policy = s3.BucketPolicy(
                to_logic_name('{}BucketPolicy'.format(bucket.title)))
            bucket_policy.Bucket = Ref(bucket)
            bucket_policy.PolicyDocument = policy
            self.template.add_resource(bucket_policy)

        rule_document = meta.get('LifecycleConfiguration')
        if rule_document:
            rules = []
            for rule in rule_document['Rules']:
                if 'Prefix' not in rule:
                    rule['Prefix'] = ''
                rules.append(s3.LifecycleRule.from_dict(title=None, d=rule))
            bucket.LifecycleConfiguration = \
                s3.LifecycleConfiguration(Rules=rules)

        cors_configuration = meta.get('cors')
        if cors_configuration:
            # breakpoint()
            cors_rules = []
            for rule in cors_configuration:
                # converting a rule to the expected format
                for key in rule.keys():
                    if key == 'Id':
                        pass
                    if isinstance(rule[key], list) \
                            or isinstance(rule[key], int):
                        pass  # expected
                    elif isinstance(rule[key], str):
                        rule[key] = [rule[key]]
                    else:
                        raise AssertionError(
                            'CORS rule attribute {0} has invalid value: {1}. '
                            'Should be str, int or list'.format(key,
                                                                rule[key]))
                cors_rules.append(s3.CorsRules.from_dict(title=None, d=rule))
            bucket.CorsConfiguration = \
                s3.CorsConfiguration(CorsRules=cors_rules)
