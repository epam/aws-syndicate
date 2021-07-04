def generate_tf_template_for_iam_role(role_name,
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


def generate_tf_template_for_iam_policy(policy_name, content):
    resource = {
        policy_name: [
            {
                "name": policy_name,
                "policy": content
            }
        ]
    }
    return resource
