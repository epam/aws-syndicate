import json

from syndicate.connection.iam_connection import build_trusted_relationships
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class IamRoleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        custom_policies = resource.get('custom_policies', [])
        predefined_policies = resource.get('predefined_policies', [])
        policies = set(custom_policies + predefined_policies)
        allowed_accounts = resource.get('allowed_accounts', [])
        principal_service = resource.get('principal_service')
        external_id = resource.get('external_id')
        trust_rltn = resource.get('trusted_relationships')

        assume_role_policy = build_trusted_relationships(
            trusted_relationships=trust_rltn, external_id=external_id,
            allowed_service=principal_service,
            allowed_account=allowed_accounts)

        policy_json = json.dumps(assume_role_policy)
        resource_template = iam_role(role_name=name,
                                     managed_policies=policies,
                                     assume_role_policy=policy_json)
        self.template.add_aws_iam_role(meta=resource_template)


def iam_role(role_name,
             managed_policies,
             assume_role_policy):
    policy_arns_exp = []
    for policy in managed_policies:
        policy_arn = f'aws_iam_policy.{policy}.arn'
        policy_exp = "${" + policy_arn + "}"
        policy_arns_exp.append(policy_exp)
    resource = {
        role_name: {
            "assume_role_policy": assume_role_policy,
            "name": role_name,
            "managed_policy_arns": policy_arns_exp
        }
    }
    return resource
