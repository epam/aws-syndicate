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
from functools import lru_cache

from boto3 import client, resource
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.iam_connection')


def get_account_role_arn(account_number):
    return "arn:aws:iam::{0}:root".format(account_number)


@apply_methods_decorator(retry())
class IAMConnection(object):
    """ IAM connection class."""

    def build_role_arn(self, role_name: str) -> str:
        from syndicate.core import CONFIG
        return f'arn:aws:iam::{CONFIG.account_id}:role' \
               f'/{CONFIG.resources_prefix}{role_name}{CONFIG.resources_suffix}'

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

    @lru_cache()
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
                           external_id=None, permissions_boundary=None):
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
            trusted_relationships = IAMConnection.empty_trusted_relationships()
        if allowed_account:
            trusted_accounts = IAMConnection.set_allowed_account(
                allowed_account, external_id, 'create')
            trusted_relationships['Statement'].append(trusted_accounts)
        if allowed_service:
            trusted_services = IAMConnection.set_allowed_service(
                allowed_service, 'create')
            trusted_relationships['Statement'].append(trusted_services)
        if isinstance(trusted_relationships, dict):
            trusted_relationships = dumps(trusted_relationships)

        params = dict(RoleName=role_name,
                      AssumeRolePolicyDocument=trusted_relationships)
        if permissions_boundary:
            params['PermissionsBoundary'] = permissions_boundary

        try:
            role = self.client.create_role(**params)
            return role['Role']
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                return self.client.get_role(role_name)['Role']
            raise e

    @staticmethod
    def empty_trusted_relationships():
        trusted_relationships = {
            "Version": "2012-10-17",
            "Statement": []
        }
        return trusted_relationships

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

    def put_role_permissions_boundary(self, role_name, policy_arn):
        _LOG.info(f'Attaching permissions boundary policy: \'{policy_arn}\''
                  f' to role: \'{role_name}\'')
        self.client.put_role_permissions_boundary(
            RoleName=role_name,
            PermissionsBoundary=policy_arn
        )

    def delete_role_permissions_boundary(self, role_name):
        _LOG.info(f'Removing permissions boundary policy from \'{role_name}\'')
        try:
            self.client.delete_role_permissions_boundary(
                RoleName=role_name
            )
        except ClientError as e:
            if 'NoSuchEntity' in str(e):
                _LOG.warn(f'Role \'{role_name}\' doesn\'t have permissions '
                          f'boundary policy. Skipping...')
            else:
                _LOG.error(str(e))
                raise e

    def get_policy_arn(self, name, policy_scope='All'):
        """ Get policy arn from list existing. To reduce list result there is
        an ability to define policy scope.

        :type policy_scope: str
        :param policy_scope: 'All'|'AWS'|'Local'
        :type name: str
        """
        # TODO this method is highly time-ineffective especially if we, for
        #  instance, perform `syndicate transform` on a big meta, where
        #  there is a huge amount of policies names.
        #  lru_cache for self.get_policies makes the situation better but in
        #  general it should be refactored.
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
        try:
            version = self.client.list_policy_versions(PolicyArn=policy_arn)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                _LOG.warn(f'Policy \'{policy_arn}\' not found')
                return
            else:
                raise e
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

    def update_custom_role(self, role, role_name, allowed_account=None,
                           allowed_service=None, trusted_relationships=None,
                           external_id=None):
        updated_role = role['AssumeRolePolicyDocument']
        if trusted_relationships:
            trusted_relationships = {
                "Version": "2012-10-17",
                "Statement": updated_role.get('Statement', [])
            }
        else:
            trusted_relationships = IAMConnection.empty_trusted_relationships()
        statement = trusted_relationships['Statement']
        if allowed_account:
            trusted_accounts = IAMConnection.set_allowed_account(
                allowed_account, external_id, 'update')
            statement.append(trusted_accounts)
        if allowed_service:
            trusted_services = IAMConnection.set_allowed_service(
                allowed_service, 'update')
            statement.append(trusted_services)
        if isinstance(trusted_relationships, dict):
            trusted_relationships = dumps(trusted_relationships)
            statement = updated_role.get('Statement', [])
            statement.append(trusted_relationships)
            unique = []
            for s in statement:
                if s not in unique:
                    unique.append(s)
        try:
            role = self.client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=trusted_relationships)
            return role['ResponseMetadata']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                _LOG.warn(f'Can not update role \'{role_name}\': role does '
                          f'not exist.')
            raise e

    @staticmethod
    def set_allowed_account(allowed_account, external_id, action):
        if isinstance(allowed_account, str):
            principal = get_account_role_arn(allowed_account)
        elif isinstance(allowed_account, list):
            principal = []
            for each in allowed_account:
                principal.append(get_account_role_arn(each))
        else:
            raise TypeError(
                f'Can not {action} role. \'allowed_account\' must be list '
                f'or string. Actual type: {type(allowed_account)}')
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
        return trusted_accounts

    @staticmethod
    def set_allowed_service(allowed_service, action):
        if isinstance(allowed_service, str):
            principal = "{0}.amazonaws.com".format(allowed_service)
        elif isinstance(allowed_service, list):
            principal = []
            for each in allowed_service:
                principal.append("{0}.amazonaws.com".format(each))
        else:
            raise TypeError(
                f'Can not {action} role. \'allowed_service\' must be list '
                f'or string. Actual type: {type(allowed_service)}')
        trusted_services = {
            "Effect": "Allow",
            "Principal": {
                "Service": principal
            },
            "Action": "sts:AssumeRole"
        }
        return trusted_services

    def update_custom_policy_content(self, name, arn, content):
        policy_resource = self.resource.Policy(arn)
        policy_json = policy_resource.default_version.document
        statement = content.get('Statement')
        if not statement:
            _LOG.warn(f'Policy \'{name}\' has no or empty \'Statement\' '
                      f'field.')
            statement = []
        policy_json['Statement'] = statement
        version = content.get('Version')
        if not statement:
            _LOG.warn(f'Policy \'{name}\' has no or empty \'Version\' '
                      f'field.')
            version = '2012-10-17'
        policy_json['Version'] = version
        policy = self.get_policy(arn=arn)
        policy_version = self.client.get_policy_version(
            PolicyArn=arn, VersionId=policy['DefaultVersionId']
        )['PolicyVersion']
        if content == policy_version['Document']:
            _LOG.warn(f'No need to update policy \'{name}\': the new and the '
                      f'old contents are identical.')
            return
        versions = self.client.list_policy_versions(PolicyArn=arn)["Versions"]
        to_remove = next((v for v in reversed(versions) if v['IsDefaultVersion'] == False), None)
        if to_remove:
            _LOG.info(f'Old version of policy is found. Removing one: {to_remove}')
            self.remove_policy_version(policy_arn=arn,
                                       version_id=to_remove['VersionId'])
        self.create_policy_version(policy_arn=arn,
                                   policy_document=dumps(policy_json),
                                   set_as_default=True)

    def create_group(self, name):
        return self.client.create_group(GroupName=name)

    def get_group(self, name):
        groups = []
        try:
            response = self.client.get_group(GroupName=name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                _LOG.warn(f'Group {name} is not found')
                return []
            raise e
        token = response.get('Marker')
        group_item = response.get('Group')
        group_item.update({'Users': response.get('Users')})
        groups.extend(group_item)
        while token:
            response = self.client.get_group(GroupName=name, Marker=token)
            token = response.get('Marker')
            group_item = response.get('Group')
            group_item.update({'Users': response.get('Users')})
            groups.extend(group_item)
        return groups

    def add_user_to_group(self, group_name, username):
        try:
            response = self.client.add_user_to_group(GroupName=group_name,
                                                     UserName=username)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                _LOG.warn(f'Group {group_name} or username {username} is not '
                          f'found')
                return []
            raise e

    def remove_user_from_group(self, group_name, username):
        try:
            response = self.client.remove_user_from_group(GroupName=group_name,
                                                          UserName=username)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                _LOG.warn(f'Group {group_name} or username {username} is not '
                          f'found')
            raise e

    def attach_group_policy(self, group_name, arn):
        try:
            response = self.client.attach_group_policy(GroupName=group_name,
                                                       PolicyArn=arn)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                _LOG.warn(f'Group {group_name} is not found')
            elif e.response['Error']['Code'] == 'LimitExceededException':
                _LOG.warn(f'Can not attach more than 10 rules to group '
                          f'{group_name}')
            raise e

    def get_waiter(self, waiter_name):
        return self.client.get_waiter(waiter_name)
