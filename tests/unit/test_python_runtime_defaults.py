import json
import unittest
from unittest.mock import MagicMock

import syndicate.core  # noqa: F401
from syndicate.connection.lambda_connection import LambdaConnection
from syndicate.core.generators.contents import (
    _generate_python_node_lambda_config,
)


class TestPythonRuntimeDefaults(unittest.TestCase):

    def test_generated_lambda_config_uses_python_314(self):
        config = json.loads(
            _generate_python_node_lambda_config(
                lambda_name='example',
                lambda_relative_path='lambdas/example',
                tags={},
            )
        )

        self.assertEqual(config['runtime'], 'python3.14')

    def test_create_lambda_uses_python_314_by_default(self):
        connection = LambdaConnection.__new__(LambdaConnection)
        connection.client = MagicMock()

        connection.create_lambda(
            lambda_name='example',
            func_name='handler.lambda_handler',
            role='example-role',
            s3_bucket='example-bucket',
            s3_key='example.zip',
        )

        request = connection.client.create_function.call_args.kwargs
        self.assertEqual(request['Runtime'], 'python3.14')


if __name__ == '__main__':
    unittest.main()
