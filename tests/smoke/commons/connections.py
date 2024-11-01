
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

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
cognito_client = boto3.client('cognito-idp', config=config)
iam_client = boto3.client('iam', config=config)
sts_client = boto3.client('sts', config=config)

ACCOUNT_ID = sts_client.get_caller_identity()['Account']


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
    response = s3_client.list_objects_v2(Bucket=bucket_name,
                                         Prefix=prefix)
    return response


def get_iam_policy(policy_name: str):
    try:
        response = iam_client.get_policy(
            PolicyArn=f'arn:aws:iam::{ACCOUNT_ID}:policy/{policy_name}')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntityException':
            print(f'No policy {policy_name}')
        return
    return response


def get_function_configuration(lambda_name: str):
    try:
        response = lambda_client.get_function_configuration(
            FunctionName=lambda_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f'No lambda {lambda_name}')
        return
    return response


def get_layer_version(lambda_layer_name: str):
    try:
        response = lambda_client.get_layer_version(LayerName=lambda_layer_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f'No lambda layer {lambda_layer_name}')
        return
    return response

