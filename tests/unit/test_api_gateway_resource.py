import unittest
from unittest.mock import MagicMock

from syndicate.core.constants import AUTHORIZATION_SCOPES_KEY
from syndicate.exceptions import InvalidValueError


class TestAuthorizationScopesValidation(unittest.TestCase):
    """Scopes MUST only work with COGNITO_USER_POOLS"""

    def setUp(self):
        from syndicate.core.resources.api_gateway_resource import \
            ApiGatewayResource

        self.mock_connection = MagicMock()
        self.mock_lambda_res = MagicMock()

        self.resource = ApiGatewayResource.__new__(ApiGatewayResource)
        self.resource.connection = self.mock_connection
        self.resource.lambda_res = self.mock_lambda_res
        self.resource.region = 'us-east-1'
        self.resource.account_id = '123456789012'

        self.mock_connection.get_model.return_value = None

    # ── POSITIVE: Cognito + scopes works ─────────────────

    def test_cognito_authorizer_with_scopes_succeeds(self):
        """COGNITO_USER_POOLS + scopes → allowed"""
        scopes = ['petstore-api/read']
        self.mock_connection.get_authorizer.return_value = {
            'type': 'COGNITO_USER_POOLS'
        }

        method_meta = {
            'authorization_type': 'my_cognito_auth',
            AUTHORIZATION_SCOPES_KEY: scopes,
            'integration_type': 'mock',
        }

        # Should NOT raise
        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={'my_cognito_auth': 'auth-id-1'}
        )

        call_kwargs = self.mock_connection.create_method.call_args
        params = call_kwargs.kwargs or call_kwargs[1]
        self.assertEqual(params.get('authorization_scopes'), scopes)

    def test_cognito_authorizer_without_scopes_succeeds(self):
        """COGNITO_USER_POOLS without scopes → allowed (uses id_token)"""
        self.mock_connection.get_authorizer.return_value = {
            'type': 'COGNITO_USER_POOLS'
        }

        method_meta = {
            'authorization_type': 'my_cognito_auth',
            'integration_type': 'mock',
        }

        # Should NOT raise
        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={'my_cognito_auth': 'auth-id-1'}
        )

        call_kwargs = self.mock_connection.create_method.call_args
        params = call_kwargs.kwargs or call_kwargs[1]
        self.assertIsNone(params.get('authorization_scopes'))

    # ── NEGATIVE: Non-Cognito + scopes raises error ──────

    def test_none_auth_with_scopes_raises_error(self):
        """NONE + scopes → InvalidValueError"""
        method_meta = {
            'authorization_type': 'NONE',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        with self.assertRaises(InvalidValueError) as ctx:
            self.resource._create_method_from_metadata(
                api_id='api-123',
                resource_id='res-456',
                resource_path='/pets',
                method='GET',
                method_meta=method_meta,
                authorizers_mapping={}
            )

        self.assertIn('COGNITO_USER_POOLS', str(ctx.exception))
        self.mock_connection.create_method.assert_not_called()

    def test_aws_iam_with_scopes_raises_error(self):
        """AWS_IAM + scopes → InvalidValueError"""
        method_meta = {
            'authorization_type': 'AWS_IAM',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        with self.assertRaises(InvalidValueError) as ctx:
            self.resource._create_method_from_metadata(
                api_id='api-123',
                resource_id='res-456',
                resource_path='/pets',
                method='GET',
                method_meta=method_meta,
                authorizers_mapping={}
            )

        self.assertIn('COGNITO_USER_POOLS', str(ctx.exception))
        self.mock_connection.create_method.assert_not_called()

    def test_custom_authorizer_with_scopes_raises_error(self):
        """CUSTOM (TOKEN) authorizer + scopes → InvalidValueError"""
        self.mock_connection.get_authorizer.return_value = {
            'type': 'TOKEN'
        }

        method_meta = {
            'authorization_type': 'my_custom_auth',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        with self.assertRaises(InvalidValueError) as ctx:
            self.resource._create_method_from_metadata(
                api_id='api-123',
                resource_id='res-456',
                resource_path='/pets',
                method='GET',
                method_meta=method_meta,
                authorizers_mapping={'my_custom_auth': 'auth-id-2'}
            )

        self.assertIn('COGNITO_USER_POOLS', str(ctx.exception))
        self.mock_connection.create_method.assert_not_called()

    def test_request_authorizer_with_scopes_raises_error(self):
        """CUSTOM (REQUEST) authorizer + scopes → InvalidValueError"""
        self.mock_connection.get_authorizer.return_value = {
            'type': 'REQUEST'
        }

        method_meta = {
            'authorization_type': 'my_request_auth',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        with self.assertRaises(InvalidValueError) as ctx:
            self.resource._create_method_from_metadata(
                api_id='api-123',
                resource_id='res-456',
                resource_path='/pets',
                method='GET',
                method_meta=method_meta,
                authorizers_mapping={'my_request_auth': 'auth-id-3'}
            )

        self.assertIn('COGNITO_USER_POOLS', str(ctx.exception))

    # ── NEGATIVE: Non-Cognito WITHOUT scopes still works ─

    def test_none_auth_without_scopes_succeeds(self):
        """NONE without scopes → works normally"""
        method_meta = {
            'authorization_type': 'NONE',
            'integration_type': 'mock',
        }

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={}
        )

        self.mock_connection.create_method.assert_called_once()

    def test_custom_authorizer_without_scopes_succeeds(self):
        """CUSTOM authorizer without scopes → works normally"""
        self.mock_connection.get_authorizer.return_value = {
            'type': 'TOKEN'
        }

        method_meta = {
            'authorization_type': 'my_custom_auth',
            'integration_type': 'mock',
        }

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={'my_custom_auth': 'auth-id-2'}
        )

        self.mock_connection.create_method.assert_called_once()


if __name__ == '__main__':
    unittest.main()