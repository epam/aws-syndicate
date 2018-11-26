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
from syndicate.core import CONFIG, CONN
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.cognito_identity_resource')
_COGNITO_IDENTITY_CONN = CONN.cognito_identity()


def cognito_resource_identifier(name, output=None):
    if output:
        # cognito currently is not located in different regions
        # process only first object
        pool_output = output.items()[0][1]
        # find id from the output
        return pool_output['description']['IdentityPoolId']
    return _COGNITO_IDENTITY_CONN.if_pool_exists_by_name(name)


def create_cognito_identity_pool(args):
    """ Create Cognito identity pool in pool in sub processes.

    :type args: list
    """
    return create_pool(_create_cognito_identity_pool_from_meta, args, 5)


def describe_cognito_pool(name, meta, pool_id=None):
    if not pool_id:
        pool_id = _COGNITO_IDENTITY_CONN.if_pool_exists_by_name(name)
    if not pool_id:
        return
    response = _COGNITO_IDENTITY_CONN.describe_identity_pool(pool_id)
    arn = 'arn:aws:cognito-identity:{0}:{1}:identitypool/{2}'.format(
        CONFIG.region, CONFIG.account_id, pool_id)
    return {
        arn: build_description_obj(response, name, meta)
    }


@unpack_kwargs
def _create_cognito_identity_pool_from_meta(name, meta):
    """ Create Cognito identity pool for authentication.

    :type name: str
    :type meta: dict
    """
    pool_id = _COGNITO_IDENTITY_CONN.if_pool_exists_by_name(name)
    if pool_id:
        _LOG.warn('%s cognito identity pool exists.', name)
        return describe_cognito_pool(name=name, meta=meta, pool_id=pool_id)

    _LOG.info('Creating identity pool %s', name)
    open_id_provider_names = meta.get('open_id_providers', [])
    open_id_arns = ['arn:aws:iam::{0}:oidc-provider/{1}'.format(
        CONFIG.account_id, n) for n in open_id_provider_names]
    pool_id = _COGNITO_IDENTITY_CONN.create_identity_pool(
        pool_name=name, provider_name=meta.get('provider_name'),
        open_id_connect_provider_arns=open_id_arns)
    auth_role = meta.get('auth_role')
    unauth_role = meta.get('unauth_role')
    if auth_role or unauth_role:
        _COGNITO_IDENTITY_CONN.set_role(pool_id, auth_role, unauth_role)
    _LOG.info('Created cognito identity pool %s', pool_id)
    return describe_cognito_pool(name=name, meta=meta, pool_id=pool_id)


def remove_cognito_identity_pools(args):
    create_pool(_remove_cognito_identity_pool, args, 5)


@unpack_kwargs
def _remove_cognito_identity_pool(arn, config):
    pool_id = config['description']['IdentityPoolId']
    try:
        _COGNITO_IDENTITY_CONN.remove_identity_pool(pool_id)
        _LOG.info('Cognito identity pool %s was removed', pool_id)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            _LOG.warn('Cognito identity pool %s is not found', id)
        else:
            raise e
