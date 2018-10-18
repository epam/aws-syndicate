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
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import retry
from syndicate.core import CONFIG, CONN
from syndicate.core.helper import create_pool, prettify_json, unpack_kwargs
from syndicate.core.resources.helper import (build_description_obj,
                                             resolve_dynamic_identifier)

_IAM_CONN = CONN.iam()

_LOG = get_logger('syndicate.core.resources.iam_resource')


def remove_policies(args):
    create_pool(_remove_policy, 3, args)


@unpack_kwargs
def _remove_policy(arn, config):
    policy_name = config['resource_name']
    try:
        _IAM_CONN.remove_policy(arn)
        _LOG.info('IAM policy %s was removed.', policy_name)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchEntity':
            _LOG.warn('IAM policy %s is not found', policy_name)
        elif error_code == 'DeleteConflict':
            _LOG.warn('Cannot remove %s policy, it is attached.',
                      policy_name)
        else:
            raise e


def remove_roles(args):
    create_pool(_remove_role, 3, args)


@unpack_kwargs
def _remove_role(arn, config):
    role_name = config['resource_name']
    try:
        attached_policies = _IAM_CONN.get_role_attached_policies(role_name)
        if attached_policies:
            _LOG.debug('Detaching policies from role %s', role_name)
            for item in attached_policies:
                _IAM_CONN.detach_policy(role_name, item.arn)
        inline_policies = _IAM_CONN.get_role_inline_policies(role_name)
        if inline_policies:
            _LOG.debug('Deleting inline policies from role %s', role_name)
            for item in inline_policies:
                item.delete()
        instance_profiles = _IAM_CONN.get_instance_profiles_for_role(role_name)
        if instance_profiles:
            for each in instance_profiles:
                _IAM_CONN.remove_role_from_instance_profile(role_name, each[
                    'InstanceProfileName'])
        _IAM_CONN.remove_role(role_name)
        _LOG.info('IAM role %s was removed.', role_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            _LOG.warn('IAM role %s is not found ', role_name)
        else:
            raise e


@retry
def _remove_instance_profile(profile_name):
    try:
        _IAM_CONN.remove_instance_profile(profile_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            _LOG.info('Instance profile %s is not found ', profile_name)
        else:
            _LOG.error('Cant remove instance profile: %s.', profile_name)
            raise e
    _LOG.info('Instance profile %s removed.', profile_name)


def create_policies(args):
    return create_pool(_create_policy_from_meta, 3, args)


def create_roles(args):
    return create_pool(_create_role_from_meta, 3, args)


@unpack_kwargs
def _create_policy_from_meta(name, meta):
    arn = _build_policy_arn(name)
    response = _IAM_CONN.get_policy(arn)
    if response:
        _LOG.warn('IAM policy %s exists.', name)
        return describe_policy(name=name, meta=meta)
    policy_content = meta['policy_content']
    _IAM_CONN.create_custom_policy(name, policy_content)
    _LOG.info('Created IAM policy %s.', name)
    return describe_policy(name=name, meta=meta)


def _build_policy_arn(name):
    return 'arn:aws:iam::{0}:policy/{1}'.format(CONFIG.account_id, name)


def describe_policy(name, meta, response=None):
    arn = _build_policy_arn(name)
    if not response:
        response = _IAM_CONN.get_policy(arn)
    del response['Arn']
    return {
        arn: build_description_obj(response, name, meta)
    }


@unpack_kwargs
def _create_role_from_meta(name, meta):
    response = _IAM_CONN.get_role(name)
    if response:
        _LOG.warn('IAM role %s exists.', name)
        return describe_role(meta, name, response)
    custom_policies = meta.get('custom_policies', [])
    predefined_policies = meta.get('predefined_policies', [])
    policies = set(custom_policies + predefined_policies)
    allowed_accounts = meta.get('allowed_accounts', [])
    principal_service = meta.get('principal_service')
    instance_profile = meta.get('instance_profile')
    external_id = meta.get('external_id')
    trust_rltn = meta.get('trusted_relationships')
    if principal_service and '{region}' in principal_service:
        principal_service = principal_service.format(region=CONFIG.region)
    response = _IAM_CONN.create_custom_role(role_name=name,
                                            allowed_account=list(
                                                allowed_accounts),
                                            allowed_service=principal_service,
                                            external_id=external_id,
                                            trusted_relationships=trust_rltn)
    if instance_profile:
        try:
            _IAM_CONN.create_instance_profile(name)
        except ClientError as e:
            if 'EntityAlreadyExists' in e.message:
                _LOG.warn('Instance profile %s exists', name)
            else:
                raise e
        _IAM_CONN.add_role_to_instance_profile(name, name)
        # attach policies
    if policies:
        for policy in policies:
            arn = _IAM_CONN.get_policy_arn(policy)
            if not arn:
                raise AssertionError('Can not get policy arn: %s.', policy)
            _IAM_CONN.attach_policy(name, arn)
    else:
        raise AssertionError('There are no policies for role: %s.', name)
    _LOG.info('Created IAM role %s.', name)
    return describe_role(meta, name, response)


def describe_role(meta, name, response=None):
    arn = response['Arn']
    if not response:
        response = _IAM_CONN.get_role(role_name=name)
    del response['Arn']
    return {
        arn: build_description_obj(response, name, meta)
    }


def apply_trusted_to_role(name, value, apply_config):
    trusted = apply_config['trusted_relationships']
    role_name = apply_config['dependency_name']
    resolved_trusted = resolve_dynamic_identifier(name, value, trusted)
    _IAM_CONN.update_assume_role_policy_document(role_name=role_name,
                                                 document=prettify_json(
                                                     resolved_trusted))


def apply_policy_content(name, value, apply_config):
    policy_content = apply_config['policy_content']
    policy_name = apply_config['dependency_name']
    resolved_policy_content = resolve_dynamic_identifier(name, value,
                                                         policy_content)
    policy_arn = 'arn:aws:iam::{0}:policy/{1}'.format(CONFIG.account_id,
                                                      policy_name)
    _IAM_CONN.create_policy_version(policy_arn=policy_arn,
                                    policy_document=prettify_json(
                                        resolved_policy_content),
                                    set_as_default=True)
