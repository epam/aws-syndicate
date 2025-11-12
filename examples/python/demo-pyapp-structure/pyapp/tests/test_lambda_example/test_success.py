from pyapp.tests.test_lambda_example import LambdaExampleLambdaTestCase


class TestSuccess(LambdaExampleLambdaTestCase):

    def test_success(self):
        self.assertEqual(self.HANDLER.handle_request(dict(), dict()), 200)

