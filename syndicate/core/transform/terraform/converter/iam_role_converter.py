import json

from syndicate.connection.iam_connection import build_trusted_relationships
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter
from syndicate.core.transform.terraform.tf_transform_helper import \
    build_policy_arn_ref


class IamRoleConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        allowed_accounts = resource.get('allowed_accounts', [])
        principal_service = resource.get('principal_service')
        external_id = resource.get('external_id')
        trust_rltn = resource.get('trusted_relationships')

        policy_arns = self._prepare_policy_arns(resource=resource)

        assume_role_policy = build_trusted_relationships(
            trusted_relationships=trust_rltn, external_id=external_id,
            allowed_service=principal_service,
            allowed_account=allowed_accounts)

        policy_json = json.dumps(assume_role_policy)
        resource_template = iam_role(role_name=name,
                                     policy_arns=policy_arns,
                                     assume_role_policy=policy_json)
        self.template.add_aws_iam_role(meta=resource_template)

    def _prepare_policy_arns(self, resource):
        custom_policies = resource.get('custom_policies', [])
        predefined_policies = resource.get('predefined_policies', [])
        policy_arns = []
        for policy in predefined_policies:
            iam_service = self.resources_provider.iam()
            policy_arn = iam_service.iam_conn.get_policy_arn(policy)
            policy_arns.append(policy_arn)
        for policy in custom_policies:
            policy_arns.append(build_policy_arn_ref(policy_name=policy))
        return policy_arns


def iam_role(role_name,
             policy_arns,
             assume_role_policy):
    resource = {
        role_name: {
            "assume_role_policy": assume_role_policy,
            "name": role_name,
            "managed_policy_arns": policy_arns
        }
    }
    return resource
