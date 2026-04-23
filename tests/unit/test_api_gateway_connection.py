import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

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


class TestUpdateIntegrationConfiguration(unittest.TestCase):
    def setUp(self):
        self.patcher = patch(
            'syndicate.connection.api_gateway_connection.boto3'
        )
        self.mock_boto3 = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.connection = ApiGatewayConnection(region='us-east-1')
        self.connection.client = self.mock_client

    def tearDown(self):
        self.patcher.stop()

    def test_raises_when_no_integration(self):
        with patch.object(
                self.connection, 'get_rest_integration', return_value=None):
            with self.assertRaises(ValueError):
                self.connection.update_integration_configuration(
                    'api-id', 'res-id', 'GET', uri='arn:new')

    def test_get_rest_integration_not_found_returns_none(self):
        self.mock_client.get_integration.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'n'}},
            'GetIntegration',
        )
        self.assertIsNone(self.connection.get_rest_integration(
            'api-id', 'res-id', 'GET'))

    def test_uri_patch_for_non_mock(self):
        self.mock_client.get_integration.return_value = {
            'type': 'AWS_PROXY',
            'httpMethod': 'POST',
            'uri': 'arn:aws:old',
            'passthroughBehavior': 'WHEN_NO_MATCH',
        }
        self.connection.update_integration_configuration(
            'api-id', 'res-id', 'GET',
            uri='arn:aws:new',
        )
        self.mock_client.update_integration.assert_called_once()
        kwargs = self.mock_client.update_integration.call_args.kwargs
        paths = [p['path'] for p in kwargs['patchOperations']]
        self.assertIn('/uri', paths)
        uri_patch = next(p for p in kwargs['patchOperations']
                         if p['path'] == '/uri')
        self.assertEqual(uri_patch['value'], 'arn:aws:new')
        self.mock_client.put_integration.assert_not_called()

    def test_integration_type_change_uses_put(self):
        self.mock_client.get_integration.return_value = {
            'type': 'MOCK',
            'httpMethod': 'POST',
            'uri': '',
            'passthroughBehavior': 'WHEN_NO_MATCH',
        }
        self.connection.update_integration_configuration(
            'api-id', 'res-id', 'GET',
            int_type='AWS_PROXY',
            integration_method='POST',
            uri='arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/'
                'functions/arn:aws:lambda:us-east-1:1:function:f/invocations',
        )
        self.mock_client.put_integration.assert_called_once()
        self.mock_client.update_integration.assert_not_called()


class TestUpdateCognitoAuthorizerUserPools(unittest.TestCase):
    def setUp(self):
        self.patcher = patch(
            'syndicate.connection.api_gateway_connection.boto3'
        )
        self.mock_boto3 = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.connection = ApiGatewayConnection(region='us-east-1')
        self.connection.client = self.mock_client

    def tearDown(self):
        self.patcher.stop()

    def test_no_pool_patches_when_arns_unchanged(self):
        arn = 'arn:aws:cognito-idp:us-east-1:1:userpool/pool-1'
        self.mock_client.get_authorizer.return_value = {
            'providerARNs': [arn],
        }
        self.connection.update_cognito_authorizer_user_pools(
            'api-id', 'auth-id', [arn],
        )
        self.mock_client.update_authorizer.assert_not_called()

    def test_replace_pool_adds_before_removes(self):
        old_arn = 'arn:aws:cognito-idp:us-east-1:1:userpool/old'
        new_arn = 'arn:aws:cognito-idp:us-east-1:1:userpool/new'
        self.mock_client.get_authorizer.return_value = {
            'providerARNs': [old_arn],
        }
        self.connection.update_cognito_authorizer_user_pools(
            'api-id', 'auth-id', [new_arn],
        )
        self.mock_client.update_authorizer.assert_called_once()
        ops = self.mock_client.update_authorizer.call_args.kwargs[
            'patchOperations']
        self.assertEqual(ops[0]['op'], 'add')
        self.assertEqual(ops[0]['path'], '/providerARNs')
        self.assertEqual(ops[0]['value'], new_arn)
        self.assertEqual(ops[1]['op'], 'remove')
        self.assertEqual(ops[1]['value'], old_arn)

    def test_removes_only_extra_pools(self):
        a = 'arn:aws:cognito-idp:us-east-1:1:userpool/a'
        b = 'arn:aws:cognito-idp:us-east-1:1:userpool/b'
        self.mock_client.get_authorizer.return_value = {
            'providerARNs': [a, b],
        }
        self.connection.update_cognito_authorizer_user_pools(
            'api-id', 'auth-id', [a],
        )
        ops = self.mock_client.update_authorizer.call_args.kwargs[
            'patchOperations']
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]['op'], 'remove')
        self.assertEqual(ops[0]['value'], b)


if __name__ == '__main__':
    unittest.main()
