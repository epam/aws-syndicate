import unittest
from unittest.mock import MagicMock

import syndicate.core  # noqa: F401
from syndicate.connection.cognito_identity_provider_connection import \
    CognitoIdentityProviderConnection
from syndicate.core.resources.cognito_user_pool_resource import \
    CognitoUserPoolResource


class TestCognitoUserPoolConfiguration(unittest.TestCase):

    def test_connection_builds_user_attribute_update_settings(self):
        connection = CognitoIdentityProviderConnection.__new__(
            CognitoIdentityProviderConnection)
        connection.client = MagicMock()
        connection.client.create_user_pool.return_value = {
            'UserPool': {'Id': 'pool-id'}
        }

        connection.create_user_pool(
            pool_name='pool',
            attributes_require_verification_before_update=[
                'email', 'phone_number'
            ])

        params = connection.client.create_user_pool.call_args.kwargs
        self.assertEqual(
            params['UserAttributeUpdateSettings'],
            {
                'AttributesRequireVerificationBeforeUpdate': [
                    'email', 'phone_number'
                ]
            })

    def test_connection_passes_token_validity_options_to_boto(self):
        connection = CognitoIdentityProviderConnection.__new__(
            CognitoIdentityProviderConnection)
        connection.client = MagicMock()
        connection.client.create_user_pool_client.return_value = {
            'UserPoolClient': {'ClientId': 'client-id'}
        }

        connection.create_user_pool_client(
            user_pool_id='pool-id',
            client_name='web-client',
            refresh_token_validity=30,
            access_token_validity=15,
            id_token_validity=20,
            token_validity_units={
                'AccessToken': 'minutes',
                'IdToken': 'minutes',
                'RefreshToken': 'days'
            },
            enable_propagate_additional_user_context_data=False,
            auth_session_validity=5,
            refresh_token_rotation={
                'Feature': 'ENABLED',
                'RetryGracePeriodSeconds': 10
            })

        params = connection.client.create_user_pool_client.call_args.kwargs
        self.assertEqual(params['RefreshTokenValidity'], 30)
        self.assertEqual(params['AccessTokenValidity'], 15)
        self.assertEqual(params['IdTokenValidity'], 20)
        self.assertEqual(
            params['TokenValidityUnits'],
            {
                'AccessToken': 'minutes',
                'IdToken': 'minutes',
                'RefreshToken': 'days'
            })
        self.assertFalse(
            params['EnablePropagateAdditionalUserContextData'])
        self.assertEqual(params['AuthSessionValidity'], 5)
        self.assertEqual(
            params['RefreshTokenRotation'],
            {'Feature': 'ENABLED', 'RetryGracePeriodSeconds': 10})

    def test_resource_converts_user_pool_and_token_unit_settings(self):
        connection = MagicMock()
        connection.if_pool_exists_by_name.return_value = None
        connection.create_user_pool.return_value = 'pool-id'
        resource = CognitoUserPoolResource(
            cognito_idp_conn=connection, account_id='123456789012',
            region='us-east-1')
        resource.describe_user_pool = MagicMock(return_value={})

        resource._create_cognito_user_pool_from_meta.__wrapped__(
            resource,
            name='pool',
            meta={
                'auto_verified_attributes': [],
                'sms_configuration': {},
                'username_attributes': [],
                'attributes_require_verification_before_update': [
                    'email', 'phone_number'
                ],
                'deletion_protection': 'ACTIVE',
                'lambda_config': {
                    'pre_sign_up': 'arn:aws:lambda:us-east-1:123456789012:'
                                   'function:pre-sign-up'
                },
                'account_recovery_setting': {
                    'recovery_mechanisms': [
                        {'name': 'verified_email', 'priority': 1}
                    ]
                },
                'verification_message_template': {
                    'email_subject': 'Verify your account',
                    'default_email_option': 'CONFIRM_WITH_CODE'
                },
                'client': {
                    'client_name': 'web-client',
                    'access_token_validity': 15,
                    'id_token_validity': 20,
                    'token_validity_units': {
                        'access_token': 'minutes',
                        'id_token': 'minutes',
                        'refresh_token': 'days'
                    },
                    'enable_propagate_additional_user_context_data': False,
                    'auth_session_validity': 5,
                    'refresh_token_rotation': {
                        'feature': 'ENABLED',
                        'retry_grace_period_seconds': 10
                    }
                }
            })

        pool_params = connection.create_user_pool.call_args.kwargs
        self.assertEqual(
            pool_params['attributes_require_verification_before_update'],
            ['email', 'phone_number'])
        self.assertEqual(pool_params['deletion_protection'], 'ACTIVE')
        self.assertEqual(
            pool_params['lambda_config'],
            {'PreSignUp': 'arn:aws:lambda:us-east-1:123456789012:'
                          'function:pre-sign-up'})
        self.assertEqual(
            pool_params['account_recovery_setting'],
            {'RecoveryMechanisms': [
                {'Name': 'verified_email', 'Priority': 1}
            ]})
        self.assertEqual(
            pool_params['verification_message_template'],
            {'EmailSubject': 'Verify your account',
             'DefaultEmailOption': 'CONFIRM_WITH_CODE'})
        client_params = connection.create_user_pool_client.call_args.kwargs
        self.assertEqual(
            client_params['token_validity_units'],
            {
                'AccessToken': 'minutes',
                'IdToken': 'minutes',
                'RefreshToken': 'days'
            })
        self.assertFalse(
            client_params[
                'enable_propagate_additional_user_context_data'])
        self.assertEqual(client_params['auth_session_validity'], 5)
        self.assertEqual(
            client_params['refresh_token_rotation'],
            {'Feature': 'ENABLED', 'RetryGracePeriodSeconds': 10})

    def test_custom_attribute_mutable_flag_is_sent_to_cognito(self):
        connection = MagicMock()
        resource = CognitoUserPoolResource(
            cognito_idp_conn=connection, account_id='123456789012',
            region='us-east-1')
        attributes = [{'name': 'department', 'type': 'String',
                       'mutable': False}]

        resource.add_custom_attributes('pool-id', attributes)

        connection.add_custom_attributes.assert_called_once_with(
            'pool-id',
            [{'Name': 'department', 'AttributeDataType': 'String',
              'Mutable': False}])
        self.assertEqual(attributes[0]['type'], 'String')


if __name__ == '__main__':
    unittest.main()
