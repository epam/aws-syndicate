import unittest

from syndicate.core.generators.deployment_resources.api_gateway_generator \
    import ApiGatewayResourceMethodGenerator


class TestMethodGeneratorConfiguration(unittest.TestCase):
    """Tests for authorization_scopes in generator CONFIGURATION"""

    def test_authorization_scopes_in_configuration(self):
        """CONFIGURATION contains authorization_scopes as list type"""
        config = ApiGatewayResourceMethodGenerator.CONFIGURATION
        self.assertIn('authorization_scopes', config)
        self.assertEqual(config['authorization_scopes'], list)

    def test_authorization_scopes_not_dict(self):
        """Ensure scopes type is list, not dict"""
        config = ApiGatewayResourceMethodGenerator.CONFIGURATION
        self.assertNotEqual(config['authorization_scopes'], dict)


if __name__ == '__main__':
    unittest.main()