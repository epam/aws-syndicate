import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from syndicate.core.constants import AUTHORIZATION_SCOPES_KEY


class TestCreateMethodFromMetadataScopes(unittest.TestCase):
    """Tests for authorization_scopes in _create_method_from_metadata"""

    def setUp(self):
        # We need to import here or mock the dependencies
        # Adjust import path based on actual module structure
        from syndicate.core.resources.api_gateway_resource import \
            ApiGatewayResource

        self.mock_connection = MagicMock()
        self.mock_lambda_res = MagicMock()

        # Create instance with mocked dependencies
        # Adjust constructor based on actual implementation
        self.resource = ApiGatewayResource.__new__(ApiGatewayResource)
        self.resource.connection = self.mock_connection
        self.resource.lambda_res = self.mock_lambda_res
        self.resource.region = 'us-east-1'
        self.resource.account_id = '123456789012'

    def _make_cognito_authorizer_mapping(self, authorizer_name,
                                          authorizer_id):
        """Helper to set up Cognito authorizer mocks"""
        mapping = {authorizer_name: authorizer_id}
        self.mock_connection.get_authorizer.return_value = {
            'type': 'COGNITO_USER_POOLS'
        }
        return mapping

    def _make_custom_authorizer_mapping(self, authorizer_name,
                                         authorizer_id):
        """Helper to set up Custom authorizer mocks"""
        mapping = {authorizer_name: authorizer_id}
        self.mock_connection.get_authorizer.return_value = {
            'type': 'TOKEN'
        }
        return mapping

    def test_cognito_authorizer_with_scopes(self):
        """Scopes ARE passed when authorizer is COGNITO_USER_POOLS"""
        scopes = ['petstore/read', 'petstore/write']
        authorizer_name = 'my_cognito_auth'
        authorizer_id = 'auth-abc123'

        mapping = self._make_cognito_authorizer_mapping(
            authorizer_name, authorizer_id)

        method_meta = {
            'authorization_type': authorizer_name,
            AUTHORIZATION_SCOPES_KEY: scopes,
            'integration_type': 'mock',
        }

        self.mock_connection.get_model.return_value = None

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping=mapping
        )

        # Verify create_method was called with scopes
        self.mock_connection.create_method.assert_called_once()
        call_kwargs = self.mock_connection.create_method.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertEqual(kwargs.get('authorization_scopes'), scopes)

    def test_cognito_authorizer_without_scopes(self):
        """No scopes passed when not configured (even with Cognito)"""
        authorizer_name = 'my_cognito_auth'
        authorizer_id = 'auth-abc123'

        mapping = self._make_cognito_authorizer_mapping(
            authorizer_name, authorizer_id)

        method_meta = {
            'authorization_type': authorizer_name,
            # No authorization_scopes key
            'integration_type': 'mock',
        }

        self.mock_connection.get_model.return_value = None

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping=mapping
        )

        call_kwargs = self.mock_connection.create_method.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertIsNone(kwargs.get('authorization_scopes'))

    def test_custom_authorizer_scopes_ignored(self):
        """Scopes are NOT passed for CUSTOM authorizer type"""
        authorizer_name = 'my_custom_auth'
        authorizer_id = 'auth-xyz789'

        mapping = self._make_custom_authorizer_mapping(
            authorizer_name, authorizer_id)

        method_meta = {
            'authorization_type': authorizer_name,
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],  # should be ignored
            'integration_type': 'mock',
        }

        self.mock_connection.get_model.return_value = None

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping=mapping
        )

        call_kwargs = self.mock_connection.create_method.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertIsNone(kwargs.get('authorization_scopes'))

    def test_none_auth_scopes_ignored(self):
        """Scopes are NOT passed for NONE authorization type"""
        method_meta = {
            'authorization_type': 'NONE',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        self.mock_connection.get_model.return_value = None

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={}
        )

        call_kwargs = self.mock_connection.create_method.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertIsNone(kwargs.get('authorization_scopes'))

    def test_aws_iam_auth_scopes_ignored(self):
        """Scopes are NOT passed for AWS_IAM authorization type"""
        method_meta = {
            'authorization_type': 'AWS_IAM',
            AUTHORIZATION_SCOPES_KEY: ['some/scope'],
            'integration_type': 'mock',
        }

        self.mock_connection.get_model.return_value = None

        self.resource._create_method_from_metadata(
            api_id='api-123',
            resource_id='res-456',
            resource_path='/pets',
            method='GET',
            method_meta=method_meta,
            authorizers_mapping={}
        )

        call_kwargs = self.mock_connection.create_method.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertIsNone(kwargs.get('authorization_scopes'))


if __name__ == '__main__':
    unittest.main()