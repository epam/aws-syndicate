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

from boto3 import client, resource
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.iam_connection')


def get_account_role_arn(account_number):
    return "arn:aws:iam::{0}:root".format(account_number)


@apply_methods_decorator(retry)
class IAMConnection(object):
    """ IAM connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('iam', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        self.resource = resource('iam', region,
                                 aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 aws_session_token=aws_session_token)
        _LOG.debug('Opened new IAM connection.')

    def check_if_role_exists(self, role_name):
        list_roles = self.get_roles()
        if list_roles:
            for each in list_roles:
                if role_name == each['RoleName']:
                    return each['Arn']

    def get_role(self, role_name):
        try:
            return self.client.get_role(RoleName=role_name)['Role']
        except ClientError as e:
            if 'NoSuchEntity' in str(e):
                pass  # valid exception
            else:
                raise e

    def get_missing_roles(self, required_roles):
        list_roles = self.get_roles()
        if list_roles:
            all_roles = [role['RoleName'] for role in list_roles]
            return [role for role in required_roles if role not in all_roles]
        else:
            return required_roles

    def get_roles(self):
        roles = []
        response = self.client.list_roles()
        token = response.get('Marker')
        roles.extend(response.get('Roles'))
        while token:
            response = self.client.list_roles(Marker=token)
            token = response.get('Marker')
            roles.extend(response.get('Roles'))
        return roles

    def get_policies(self, scope='All', only_attached=False):
        """
        :param scope: 'All'|'AWS'|'Local'
        :type only_attached: bool
        """
        policies = []
        response = self.client.list_policies(
            Scope=scope,
            OnlyAttached=only_attached
        )
        token = response.get('Marker')
        policies.extend(response.get('Policies'))
        while token:
            response = self.client.list_policies(
                Scope=scope,
                OnlyAttached=only_attached,
                Marker=token
            )
            token = response.get('Marker')
            policies.extend(response.get('Policies'))
        return policies

    def get_role_attached_policies(self, role_name):
        role = self.resource.Role(role_name)
        return role.attached_policies.all()

    def get_role_inline_policies(self, role_name):
        role = self.resource.Role(role_name)
        return role.policies.all()

    def get_role_names(self):
        roles = self.get_roles()
        return [each['RoleName'] for each in roles]

    def get_attached_policy_content(self, policy_arn):
        """ Get content from policy: latest version.

        :type policy_arn: str
        """
        version = self.client.list_policy_versions(PolicyArn=policy_arn)
        policy_version = version['Versions'][0]['VersionId']
        policy_content = self.client.get_policy_version(
            PolicyArn=policy_arn, VersionId=policy_version)
        return policy_content['PolicyVersion']['Document']

    def create_custom_policy(self, policy_name, policy_document):
        """
        :type policy_name: str
        :type policy_document: dict or str
        """
        if isinstance(policy_document, dict):
            policy_document = dumps(policy_document)
        return self.client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )['Policy']

    def create_custom_role(self, role_name, allowed_account=None,
                           allowed_service=None, trusted_relationships=None,
                           external_id=None):
        """ Create custom role with trusted relationships. You can specify
        custom policy, or set principal_account and principal_service params
        to use default.

        :type role_name: str
        :type allowed_account: str (acc id)
        :type allowed_service: str
        :type trusted_relationships: dict
        :param trusted_relationships: if not specified will use default
        """
        if not trusted_relationships:
            trusted_relationships = {
                "Version": "2012-10-17",
                "Statement": []
            }
            if allowed_account:
                if isinstance(allowed_account, str):
                    principal = get_account_role_arn(allowed_account)
                elif isinstance(allowed_account, list):
                    principal = []
                    for each in allowed_account:
                        principal.append(get_account_role_arn(each))
                else:
                    raise TypeError(
                        'Can not create role. allowed_account must be list or '
                        'str. Actual type: {0}'.format(type(allowed_account)))
                trusted_accounts = {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": principal
                    },
                    "Action": "sts:AssumeRole"
                }
                if external_id:
                    trusted_accounts['Condition'] = {
                        "StringEquals": {
                            "sts:ExternalId": external_id
                        }
                    }
                trusted_relationships['Statement'].append(trusted_accounts)
        if allowed_service:
            if isinstance(allowed_service, str):
                principal = "{0}.amazonaws.com".format(allowed_service)
            elif isinstance(allowed_service, list):
                principal = []
                for each in allowed_service:
                    principal.append("{0}.amazonaws.com".format(each))
            else:
                raise TypeError(
                    'Can not create role. allowed_service must be list or '
                    'str. Actual type: {0}'.format(type(allowed_service)))
            trusted_services = {
                "Effect": "Allow",
                "Principal": {
                    "Service": principal
                },
                "Action": "sts:AssumeRole"
            }
            trusted_relationships['Statement'].append(trusted_services)
        if isinstance(trusted_relationships, dict):
            trusted_relationships = dumps(trusted_relationships)

        try:
            role = self.client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=trusted_relationships)
            return role['Role']
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                return self.client.get_role(role_name)['Role']
            raise e

    def attach_policy(self, role_name, policy_arn):
        self.client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )

    def attach_inline_policy(self, role_name, policy_name, policy_document):
        if isinstance(policy_document, dict):
            policy_document = dumps(policy_document)
        self.client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )

    def detach_policy(self, role_name, policy_arn):
        self.client.detach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )

    def get_policy_arn(self, name, policy_scope='All'):
        """ Get policy arn from list existing. To reduce list result there is
        an ability to define policy scope.

        :type policy_scope: str
        :param policy_scope: 'All'|'AWS'|'Local'
        :type name: str
        """
        custom_policies = self.get_policies(policy_scope)
        for each in custom_policies:
            if each['PolicyName'] == name:
                return each['Arn']

    def get_policy(self, arn):
        try:
            return self.client.get_policy(PolicyArn=arn)['Policy']
        except ClientError as e:
            if 'NoSuchEntity' in str(e):
                pass  # valid exception
            else:
                raise e

    def remove_policy_version(self, policy_arn, version_id):
        self.client.delete_policy_version(
            PolicyArn=policy_arn,
            VersionId=version_id
        )

    def create_policy_version(self, policy_arn, policy_document,
                              set_as_default=None):
        params = dict(PolicyArn=policy_arn,
                      PolicyDocument=policy_document)
        if set_as_default:
            params['SetAsDefault'] = set_as_default
        self.client.create_policy_version(**params)

    def remove_policy(self, policy_arn):
        """ To remove policy all it version must be removed before default one.

        :type policy_arn: str
        """
        version = self.client.list_policy_versions(PolicyArn=policy_arn)
        policy_versions = version['Versions']
        if policy_versions:
            for each in policy_versions:
                if each['IsDefaultVersion']:
                    continue
                self.remove_policy_version(policy_arn, each['VersionId'])
        self.client.delete_policy(PolicyArn=policy_arn)

    def remove_role(self, role_name):
        self.client.delete_role(RoleName=role_name)

    def create_instance_profile(self, profile_name):
        self.client.create_instance_profile(
            InstanceProfileName=profile_name
        )

    def remove_instance_profile(self, profile_name):
        self.client.delete_instance_profile(
            InstanceProfileName=profile_name
        )

    def get_instance_profiles(self):
        profiles = []
        response = self.client.list_instance_profiles()
        token = response.get('Marker')
        profiles.extend(response.get('InstanceProfiles'))
        while token:
            response = self.client.list_instance_profiles(Marker=token)
            token = response.get('Marker')
            profiles.extend(response.get('InstanceProfiles'))
        return profiles

    def is_instance_profile_exists(self, profile_name):
        profiles = self.get_instance_profiles()
        for each in profiles:
            if each['InstanceProfileName'] == profile_name:
                return each

    def add_role_to_instance_profile(self, profile_name, role_name):
        self.client.add_role_to_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name
        )

    def remove_role_from_instance_profile(self, profile_name, role_name):
        self.client.remove_role_from_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name
        )

    def get_instance_profiles_for_role(self, role_name):
        profiles = []
        response = self.client.list_instance_profiles_for_role(
            RoleName=role_name
        )
        token = response.get('Marker')
        profiles.extend(response.get('InstanceProfiles'))
        while token:
            response = self.client.list_instance_profiles_for_role(
                RoleName=role_name, Marker=token
            )
            token = response.get('Marker')
            profiles.extend(response.get('InstanceProfiles'))
        return profiles

    def get_assume_role_policy_document(self, role_name):
        return self.resource.Role(role_name).assume_role_policy_document

    def update_assume_role_policy_document(self, role_name, document):
        self.resource.AssumeRolePolicy(role_name).update(
            PolicyDocument=document)

    def create_user(self, name, path=None):
        params = dict(UserName=name)
        if path:
            params['Path'] = path
        return self.client.create_user(**params)

    def delete_user(self, name):
        self.client.delete_user(UserName=name)

    def attach_policy_to_user(self, name, policy_arn):
        params = dict(UserName=name, PolicyArn=policy_arn)
        self.client.attach_user_policy(**params)

    def create_access_key(self, user_name):
        return self.client.create_access_key(UserName=user_name)

    def get_users(self, path=None):
        users = []
        params = dict()
        if path:
            params['PathPrefix'] = path
        response = self.client.list_users(**params)
        users.extend(response.get('Users'))
        token = response.get('Marker')
        while token:
            params['Marker'] = token
            response = self.client.list_users(**params)
            token = response.get('Marker')
            users.extend(response.get('Users'))
        return users

    def is_user_exists(self, user_name):
        list_users = self.get_users()
        if list_users:
            for each in list_users:
                if user_name == each['UserName']:
                    return each['Arn']

    def get_access_keys(self, user_name):
        keys = []
        response = self.client.list_access_keys(UserName=user_name)
        keys.extend(response.get('AccessKeyMetadata'))
        token = response.get('Marker')
        while token:
            response = self.client.list_access_keys(UserName=user_name,
                                                    Marker=token)
            token = response.get('Marker')
            keys.extend(response.get('AccessKeyMetadata'))
        return keys

    def delete_access_key(self, user_name, access_key):
        self.client.delete_access_key(AccessKeyId=access_key,
                                      UserName=user_name)

    def get_user_attached_policies(self, user_name, path=None):
        policies = []
        params = dict(UserName=user_name)
        if path:
            params['PathPrefix'] = path
        response = self.client.list_attached_user_policies(**params)
        policies.extend(response.get('AttachedPolicies'))
        token = response.get('Marker')
        while token:
            params['Marker'] = token
            response = self.client.list_attached_user_policies(**params)
            token = response.get('Marker')
            policies.extend(response.get('AttachedPolicies'))
        return policies

    def detach_user_policy(self, user_name, policy_arn):
        self.client.detach_user_policy(UserName=user_name,
                                       PolicyArn=policy_arn)

    def get_user_certificates(self, user_name):
        certs = []
        response = self.client.list_signing_certificates(UserName=user_name)
        certs.extend(response.get('Certificates'))
        token = response.get('Marker')
        while token:
            response = self.client.list_signing_certificates(
                UserName=user_name,
                Marker=token)
            token = response.get('Marker')
            certs.extend(response.get('Certificates'))
        return certs

    def delete_user_certificate(self, user_name, cert_id):
        self.client.delete_signing_certificate(UserName=user_name,
                                               CertificateId=cert_id)

    def get_user_ssh_keys(self, user_name):
        ssh_keys = []
        response = self.client.list_ssh_public_keys(UserName=user_name)
        ssh_keys.extend(response.get('SSHPublicKeys'))
        token = response.get('Marker')
        while token:
            response = self.client.list_ssh_public_keys(UserName=user_name,
                                                        Marker=token)
            token = response.get('Marker')
            ssh_keys.extend(response.get('SSHPublicKeys'))
        return ssh_keys

    def delete_user_ssh_key(self, user_name, ssh_id):
        self.client.delete_ssh_public_key(UserName=user_name,
                                          SSHPublicKeyId=ssh_id)

    def get_user_inline_policies(self, user_name):
        policies = []
        response = self.client.list_user_policies(UserName=user_name)
        policies.extend(response.get('PolicyNames'))
        token = response.get('Marker')
        while token:
            response = self.client.list_user_policies(UserName=user_name,
                                                      Marker=token)
            token = response.get('Marker')
            policies.extend(response.get('PolicyNames'))
        return policies
