from pyapp.tests.test_sdct_at_python_lambda import SdctAtPythonLambdaLambdaTestCase


class TestSuccess(SdctAtPythonLambdaLambdaTestCase):

    def test_success(self):
        self.assertEqual(self.HANDLER.handle_request(dict(), dict()), 200)

