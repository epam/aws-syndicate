import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class S3BucketConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        acl = resource.get('acl')
        policy = resource.get('policy')
        s3_bucket_meta = s3_bucket(bucket_name=name, acl=acl,
                                   policy=json.dumps(policy))
        self.template.add_aws_s3_bucket(meta=s3_bucket_meta)


def s3_bucket(bucket_name, acl, policy):
    resource = {
        bucket_name:
            {
                "acl": acl,
                "bucket": bucket_name,
                "policy": policy
            }

    }
    return resource
