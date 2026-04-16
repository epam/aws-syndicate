import unittest
from unittest.mock import MagicMock

import syndicate.core # noqa: F401
from syndicate.connection.api_gateway_connection import (
    ApiGatewayConnection)


class TestCreateMethodAuthorizationScopes(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock()
        self.connection = ApiGatewayConnection.__new__(
            ApiGatewayConnection)
        self.connection.client = self.mock_client

    def test_with_scopes(self):
        """authorizationScopes passed when provided"""
        scopes = ['petstore/read', 'petstore/write']

        self.connection.create_method(
            api_id='api-1',
            resource_id='res-1',
            method='GET',
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=scopes,
        )

        call_kwargs = self.mock_client.put_method.call_args
        actual = call_kwargs.kwargs or call_kwargs[1]
        self.assertEqual(actual['authorizationScopes'], scopes)

    def test_without_scopes(self):
        """authorizationScopes NOT in params when None"""
        self.connection.create_method(
            api_id='api-1',
            resource_id='res-1',
            method='GET',
            authorization_type='NONE',
            authorization_scopes=None,
        )

        call_kwargs = self.mock_client.put_method.call_args
        actual = call_kwargs.kwargs or call_kwargs[1]
        self.assertNotIn('authorizationScopes', actual)

    def test_empty_scopes(self):
        """authorizationScopes NOT in params when empty list"""
        self.connection.create_method(
            api_id='api-1',
            resource_id='res-1',
            method='GET',
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=[],
        )

        call_kwargs = self.mock_client.put_method.call_args
        actual = call_kwargs.kwargs or call_kwargs[1]
        self.assertNotIn('authorizationScopes', actual)

    def test_single_scope(self):
        """Single scope works"""
        self.connection.create_method(
            api_id='api-1',
            resource_id='res-1',
            method='GET',
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=['openid'],
        )

        call_kwargs = self.mock_client.put_method.call_args
        actual = call_kwargs.kwargs or call_kwargs[1]
        self.assertEqual(actual['authorizationScopes'], ['openid'])


if __name__ == '__main__':
    unittest.main()