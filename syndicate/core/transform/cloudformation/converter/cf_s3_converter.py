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
from troposphere import s3

from .cf_resource_converter import CfResourceConverter
from ..cf_transform_utils import to_logic_name, s3_bucket_logic_name

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
        bucket = s3.Bucket(s3_bucket_logic_name(name))
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
                to_logic_name('S3BucketPolicy', bucket.title))
            bucket_policy.Bucket = bucket.ref()
            bucket_policy.PolicyDocument = policy
            self.template.add_resource(bucket_policy)

        rule_document = meta.get('LifecycleConfiguration')
        if rule_document:
            rules = []
            for rule in rule_document['Rules']:
                if 'Prefix' not in rule:
                    rule['Prefix'] = ''
                rule_id = rule.pop('ID', None)
                if rule_id:
                    rule['Id'] = rule_id
                expiration = rule.pop('Expiration', None)
                if expiration:
                    if expiration.get('Date'):
                        rule['ExpirationDate'] = expiration.get('Date')
                    if expiration.get('Days'):
                        rule['ExpirationInDays'] = expiration.get('Days')
                    delete_marker = expiration.get('ExpiredObjectDeleteMarker')
                    if delete_marker:
                        rule['ExpiredObjectDeleteMarker'] = delete_marker
                transitions = rule.get('Transitions')
                if transitions:
                    for each in transitions:
                        transition_date = each.pop('Date', None)
                        transition_days = each.pop('Days', None)
                        if transition_date:
                            each['TransitionDate'] = transition_date
                        if transition_days:
                            each['TransitionInDays'] = transition_days
                rules.append(s3.LifecycleRule.from_dict(title=None, d=rule))
            bucket.LifecycleConfiguration = \
                s3.LifecycleConfiguration(Rules=rules)

        cors_configuration = meta.get('cors')
        if cors_configuration:
            cors_rules = []
            for rule in cors_configuration:
                # converting a rule to the expected format
                for key in list(rule.keys()):
                    new_key = key
                    if key == 'ID':
                        rule['Id'] = rule.pop(key)
                        continue
                    elif key == 'ExposeHeaders':
                        new_key = 'ExposedHeaders'
                        rule[new_key] = rule.pop(key)
                    elif key == 'MaxAgeSeconds':
                        new_key = 'MaxAge'
                        rule[new_key] = rule.pop(key)
                    if isinstance(rule[new_key], list) \
                            or isinstance(rule[new_key], int):
                        pass  # expected
                    elif isinstance(rule[new_key], str):
                        rule[new_key] = [rule[new_key]]
                    else:
                        raise AssertionError(
                            'CORS rule attribute {0} has invalid value: {1}. '
                            'Should be str, int or list'.format(key,
                                                                rule[key]))
                cors_rules.append(s3.CorsRules.from_dict(title=None, d=rule))
            bucket.CorsConfiguration = \
                s3.CorsConfiguration(CorsRules=cors_rules)

    @staticmethod
    def configure_event_source_for_lambda(bucket, lambda_arn, events,
                                          filter_rules=None):
        try:
            notification_config = bucket.NotificationConfiguration
        except AttributeError:
            notification_config = s3.NotificationConfiguration()
            bucket.NotificationConfiguration = notification_config
        configs = []
        for event in events:
            config = s3.LambdaConfigurations(Event=event,
                                             Function=lambda_arn)
            configs.append(config)
            if filter_rules:
                rules = []
                for rule in filter_rules:
                    rules.append(s3.Rules(Name=rule['Name'],
                                          Value=rule['Value']))
                s3_key = s3.S3Key(Rules=rules)
                config.Filter = s3.Filter(S3Key=s3_key)
        try:
            existing_configs = notification_config.LambdaConfigurations
            existing_configs.extend(configs)
        except AttributeError:
            notification_config.LambdaConfigurations = configs
