
import boto3
from botocore.config import Config


config = Config(
   retries={
      'max_attempts': 10,
      'mode': 'standard'
   }
)

session = boto3.session.Session()
lambda_client = boto3.client('lambda', config=config)
api_gw_client = boto3.client('apigateway', config=config)
sqs_client = boto3.client('sqs', config=config)
sns_client = boto3.client('sns', config=config)
logs_client = boto3.client('logs', config=config)
dynamodb_client = boto3.client('dynamodb', config=config)
dynamodb = boto3.resource('dynamodb', config=config)
xray_client = boto3.client('xray', config=config)
eventbridge_client = boto3.client('events', config=config)
s3_client = boto3.client('s3', config=config)
cognito_client = boto3.client("cognito-idp", config=config)


def get_lambda_alias(function_name, alias_name):
    try:
        return lambda_client.get_alias(FunctionName=function_name,
                                       Name=alias_name)
    except lambda_client.exceptions.ResourceNotFoundException:
        return None


def get_s3_bucket_file_content(bucket_name, file_key):
    file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return file_obj["Body"].read()


def get_s3_bucket_object(bucket_name, file_key):
    file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return file_obj


def get_s3_list_objects(bucket_name, prefix=None):
    files = s3_client.list_objects_v2(Bucket=bucket_name,
                                      Prefix=prefix)
    return files
