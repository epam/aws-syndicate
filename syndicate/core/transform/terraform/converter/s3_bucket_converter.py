import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class S3BucketConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        acl = resource.get('acl')
        policy = resource.get('policy')
        rule_document = resource.get('LifecycleConfiguration')
        # if rule_document:
        #     rules = []
        #     for rule in rule_document['Rules']:
        #         if 'Prefix' not in rule:
        #             rule['Prefix'] = ''
        #
        # cors_configuration = resource.get('cors')
        # if cors_configuration:
        #     rules = []
        #     for rule in cors_configuration:
        #         for key in rule.keys():
        #             if isinstance(rule[key], list) \
        #                     or isinstance(rule[key], int):
        #                 pass  # expected
        #             elif isinstance(rule[key], str):
        #                 rule[key] = [rule[key]]
        #             else:
        #                 raise AssertionError(
        #                     'Value of CORS rule attribute {0} has invalid '
        #                     'value: {1}. Should be str, int or list'.format(
        #                         key,
        #                         rule[
        #                             key]))
        #         rules.append(rule)

        s3_bucket_meta = s3_bucket(bucket_name=name, acl=acl,
                                   policy=json.dumps(policy))
        self.template.add_aws_s3_bucket(meta=s3_bucket_meta)


def s3_bucket(bucket_name, acl, policy, cors_rules=None):
    s3_bucket = {
        "acl": acl,
        "bucket": bucket_name,
        "policy": policy
    }

    resource = {
        bucket_name: s3_bucket

    }
    return resource
