import unittest
from unittest.mock import MagicMock, patch

from syndicate.connection.api_gateway_connection import ApiGatewayConnection


class TestCreateMethodAuthorizationScopes(unittest.TestCase):
    """Tests for authorization_scopes support in create_method"""

    def setUp(self):
        self.patcher = patch(
            'syndicate.connection.api_gateway_connection.boto3'
        )
        self.mock_boto3 = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client

        self.connection = ApiGatewayConnection(region='us-east-1')
        # Override client directly if constructor differs
        self.connection.client = self.mock_client

        self.base_params = {
            'api_id': 'test-api-id',
            'resource_id': 'test-resource-id',
            'method': 'GET',
        }

    def tearDown(self):
        self.patcher.stop()

    def test_create_method_with_scopes(self):
        """authorizationScopes IS included when scopes are provided"""
        scopes = ['petstore/read', 'petstore/write']

        self.connection.create_method(
            **self.base_params,
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=scopes
        )

        call_kwargs = self.mock_client.put_method.call_args
        self.assertIn('authorizationScopes', call_kwargs[1]
                      if call_kwargs[1] else call_kwargs[0])

        actual_params = (call_kwargs[1] if call_kwargs[1]
                         else dict(zip(
                             ['restApiId', 'resourceId', 'httpMethod'],
                             call_kwargs[0])))

        # Safer: just check the actual call
        self.mock_client.put_method.assert_called_once()
        actual = self.mock_client.put_method.call_args
        self.assertEqual(
            actual.kwargs.get('authorizationScopes',
                              actual[1].get('authorizationScopes')),
            scopes
        )

    def test_create_method_without_scopes(self):
        """authorizationScopes is NOT included when scopes are None"""
        self.connection.create_method(
            **self.base_params,
            authorization_type='NONE',
            authorization_scopes=None
        )

        self.mock_client.put_method.assert_called_once()
        call_kwargs = self.mock_client.put_method.call_args
        # Should not contain authorizationScopes at all
        if call_kwargs.kwargs:
            self.assertNotIn('authorizationScopes', call_kwargs.kwargs)
        else:
            self.assertNotIn('authorizationScopes', call_kwargs[1])

    def test_create_method_with_empty_list_scopes(self):
        """authorizationScopes is NOT included when scopes are empty list"""
        self.connection.create_method(
            **self.base_params,
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=[]
        )

        self.mock_client.put_method.assert_called_once()
        call_args = self.mock_client.put_method.call_args
        # Empty list is falsy → should be excluded
        self.assertNotIn('authorizationScopes',
                         call_args.kwargs if call_args.kwargs
                         else call_args[1])

    def test_create_method_scopes_with_all_other_params(self):
        """Scopes work alongside all other optional parameters"""
        scopes = ['api/read']

        self.connection.create_method(
            **self.base_params,
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            api_key_required=True,
            request_parameters={'method.request.header.X-Custom': True},
            request_models={'application/json': 'MyModel'},
            request_validator='validator-123',
            authorization_scopes=scopes
        )

        self.mock_client.put_method.assert_called_once()
        call_kwargs = self.mock_client.put_method.call_args
        params = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

        self.assertEqual(params['authorizationScopes'], scopes)
        self.assertEqual(params['authorizerId'], 'auth-123')
        self.assertTrue(params['apiKeyRequired'])
        self.assertIn('requestParameters', params)
        self.assertIn('requestModels', params)
        self.assertIn('requestValidatorId', params)

    def test_create_method_single_scope(self):
        """Single scope in list works correctly"""
        scopes = ['openid']

        self.connection.create_method(
            **self.base_params,
            authorization_type='COGNITO_USER_POOLS',
            authorizer_id='auth-123',
            authorization_scopes=scopes
        )

        call_kwargs = self.mock_client.put_method.call_args
        params = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        self.assertEqual(params['authorizationScopes'], ['openid'])


if __name__ == '__main__':
    unittest.main()