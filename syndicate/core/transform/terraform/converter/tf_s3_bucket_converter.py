import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class S3BucketConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        acl = resource.get('acl')
        policy = resource.get('policy')

        rule_document = resource.get('LifecycleConfiguration')
        rules = []
        if rule_document:
            for rule in rule_document['Rules']:
                if 'Prefix' not in rule:
                    rule['Prefix'] = ''
                rules.append(rule)

        cors_configuration = resource.get('cors')
        if cors_configuration:
            for rule in cors_configuration:
                for key in rule.keys():
                    if isinstance(rule[key], list) \
                            or isinstance(rule[key], int):
                        pass  # expected
                    elif isinstance(rule[key], str):
                        rule[key] = [rule[key]]
                    else:
                        raise AssertionError(
                            'Value of CORS rule attribute {0} has invalid '
                            'value: {1}. Should be str, int or list'.format(
                                key, rule[key]))

        s3_bucket_meta = s3_bucket(bucket_name=name, acl=acl,
                                   policy=json.dumps(policy),
                                   cors_rules=cors_configuration,
                                   lifecycle_rules=rules)
        self.template.add_aws_s3_bucket(meta=s3_bucket_meta)


def s3_bucket(bucket_name, acl, policy, cors_rules=None, lifecycle_rules=None):
    s3_bucket = {
        "acl": acl,
        "bucket": bucket_name
    }

    if policy:
        s3_bucket['policy'] = policy

    cors = []
    if cors_rules:
        for rule in cors_rules:
            cors.append(
                {
                    'allowed_headers': rule['AllowedHeaders'],
                    'allowed_methods': rule['AllowedMethods'],
                    'allowed_origins': rule['AllowedOrigins'],
                    'expose_headers': rule['ExposeHeaders'],
                    'max_age_seconds': rule['MaxAgeSeconds']
                }
            )
    if cors:
        s3_bucket['cors_rule'] = cors

    rules = []
    if lifecycle_rules:
        for rule in lifecycle_rules:
            transitions = []
            for transition in rule['Transitions']:
                transitions.append(
                    {
                        'days': int(transition['Days']),
                        'storage_class': transition['StorageClass']
                    }
                )
            rules.append(
                {
                    'id': rule['ID'],
                    'prefix': rule['Prefix'],
                    'enabled': True if rule['Status'] == 'Enabled' else False,
                    'expiration': {
                        'days': int(rule['Expiration']['Days'])
                    },
                    'transition': transitions
                }
            )
    if rules:
        s3_bucket['lifecycle_rule'] = rules

    resource = {
        bucket_name: s3_bucket

    }
    return resource
