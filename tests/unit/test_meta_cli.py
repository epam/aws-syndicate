import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from syndicate.core.groups.meta import api_gateway_resource_method


class TestAuthorizationScopesCLI(unittest.TestCase):
    """Tests for --authorization-scopes CLI option"""

    def setUp(self):
        self.runner = CliRunner()

    @patch('syndicate.core.groups.meta._generate')
    @patch('syndicate.core.groups.meta.ApiGatewayResourceMethodGenerator')
    def test_scopes_passed_to_generator(self, mock_generator_cls,
                                         mock_generate):
        """Scopes from CLI are passed through to generator"""
        mock_generator_cls.return_value = MagicMock()

        result = self.runner.invoke(
            api_gateway_resource_method,
            [
                '--api-name', 'test-api',
                '--path', '/pets',
                '--method', 'GET',
                '--authorization-scopes', 'petstore/read',
                '--authorization-scopes', 'petstore/write',
            ],
            obj={'project_path': '/tmp/test'},
            catch_exceptions=False
        )

        mock_generator_cls.assert_called_once()
        call_kwargs = mock_generator_cls.call_args.kwargs \
            if mock_generator_cls.call_args.kwargs \
            else mock_generator_cls.call_args[1]

        self.assertIn('authorization_scopes', call_kwargs)
        self.assertEqual(
            set(call_kwargs['authorization_scopes']),
            {'petstore/read', 'petstore/write'}
        )

    @patch('syndicate.core.groups.meta._generate')
    @patch('syndicate.core.groups.meta.ApiGatewayResourceMethodGenerator')
    def test_empty_scopes_removed(self, mock_generator_cls, mock_generate):
        """Empty scopes tuple is cleaned up before reaching generator"""
        mock_generator_cls.return_value = MagicMock()

        result = self.runner.invoke(
            api_gateway_resource_method,
            [
                '--api-name', 'test-api',
                '--path', '/pets',
                '--method', 'GET',
                # No --authorization-scopes provided
            ],
            obj={'project_path': '/tmp/test'},
            catch_exceptions=False
        )

        mock_generator_cls.assert_called_once()
        call_kwargs = mock_generator_cls.call_args.kwargs \
            if mock_generator_cls.call_args.kwargs \
            else mock_generator_cls.call_args[1]

        # Should not be present OR should be None
        scopes = call_kwargs.get('authorization_scopes')
        self.assertFalse(scopes)  # None or empty


if __name__ == '__main__':
    unittest.main()