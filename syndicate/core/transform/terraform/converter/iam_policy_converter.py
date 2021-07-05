import json

from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class IamPolicyConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        policy = resource.get('policy_content')
        policy_content = json.dumps(policy)

        resource_template = iam_policy(
            policy_name=name,
            content=policy_content)
        self.template.add_aws_iam_policy(meta=resource_template)


def iam_policy(policy_name, content):
    resource = {
        policy_name:
            {
                "name": policy_name,
                "policy": content
            }
    }
    return resource
