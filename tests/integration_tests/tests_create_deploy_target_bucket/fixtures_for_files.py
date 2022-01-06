BOTO3_INIT = """
from unittest import mock

client = mock.Mock()


class MockedRes(mock.MagicMock):

    def __call__(self, *args, **kwargs):
        print(args)
        print(kwargs)
        return super(MockedRes, self).__call__(*args, **kwargs)


resource = MockedRes()
"""

BOTO3_SESSION = """
from unittest import mock

Session = mock.Mock()
"""

BOTO3_DYNAMODB_CONDITIONS = """
from unittest import mock

Attr = mock.Mock()
Key = mock.Mock()
"""

SDCT_CONFIG = """
# base config data
region=eu-central-1
account_id=123456789789


aws_access_key_id=TYPE_YOUR_ACCESS_KEY_ID
aws_secret_access_key= TYPE_YOUR_SECRET_ACCESS_KEY

# build configuration
build_projects_mapping=python:/python-demo
"""