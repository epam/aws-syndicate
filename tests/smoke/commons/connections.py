from typing import Union

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from smoke.commons.constants import DEPLOY_OUTPUT_DIR
from smoke.commons.utils import deep_get

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
REGION = sts_client.meta.region_name


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
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    except s3_client.exceptions.NoSuchKey:
        print(f'Not found key {file_key} in the bucket {bucket_name}')
        return
    return file_obj


def get_s3_list_objects(bucket_name, prefix=None):
    response = s3_client.list_objects_v2(Bucket=bucket_name,
                                         Prefix=prefix)
    return response


def get_iam_policy(policy_name: str) -> Union[dict | None]:
    try:
        response = iam_client.get_policy(
            PolicyArn=f'arn:aws:iam::{ACCOUNT_ID}:policy/{policy_name}')
    except iam_client.exceptions.ResourceNotFoundException:
        print(f'Policy \'{policy_name}\' not found')
        return
    return response


def get_iam_role(role_name: str) -> Union[dict | None]:
    try:
        response = iam_client.get_role(RoleName=role_name)['Role']
    except iam_client.exceptions.ResourceNotFoundException:
        print(f'Role \'{role_name}\' not found')
        return
    return response


def get_function_configuration(lambda_name: str) -> Union[dict | None]:
    try:
        response = lambda_client.get_function_configuration(
            FunctionName=lambda_name)
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f'Lambda \'{lambda_name}\' not found')
        return
    return response


def get_layer_version(lambda_layer_name: str) -> Union[dict | None]:
    try:
        response = lambda_client.list_layer_versions(
            LayerName=lambda_layer_name)
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f'Lambda layer \'{lambda_layer_name}\' not found')
        return
    return response


def get_api_gw_id(api_gw_name: str) -> Union[str | None]:
    try:
        paginator = api_gw_client.get_paginator('get_rest_apis')
        for response in paginator.paginate():
            for api in response['items']:
                if api['name'] == api_gw_name:
                    return api['id']
    except api_gw_client.exceptions.ResourceNotFoundException:
        print(f'API Gateway \'{api_gw_name}\' not found')
    return


def get_sqs_queue_url(sqs_queue_name: str) -> Union[str | None]:
    try:
        response = sqs_client.get_queue_url(QueueName=sqs_queue_name)
    except sqs_client.exceptions.QueueDoesNotExist:
        print(f'Queue \'{sqs_queue_name}\' not found')
        return
    return response['QueueUrl']


def get_sns_topic_attributes(name: str) -> Union[dict | None]:
    topic_arn = f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:{name}'
    try:
        response = sns_client.get_topic_attributes(TopicArn=topic_arn)
    except sns_client.exceptions.NotFoundException:
        print(f'Topic \'{name}\' noy found')
        return
    return response


def get_dynamodb_table_description(name: str) -> Union[dict | None]:
    try:
        result = dynamodb_client.describe_table(TableName=name)
    except dynamodb_client.exceptions.ResourceNotFoundException:
        print(f'Table \'{name}\' not found')
        return
    return result


def get_event_bridge_rule(name: str) -> Union[dict | None]:
    try:
        response = eventbridge_client.describe_rule(Name=name)
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f'Rule \'{name}\' not found')
        return
    return response


def get_s3_bucket_head(name: str) -> Union[dict | None]:
    try:
        response = s3_client.head_bucket(Bucket=name)
    except s3_client.exceptions.NoSuchBucket:
        print(f'Bucket \'{name}\' not found')
        return
    return response


def get_s3_bucket_website(name: str) -> Union[dict | None]:
    try:
        response = s3_client.get_bucket_website(Bucket=name)
    except ClientError as e:
        if 'NoSuchWebsiteConfiguration' in str(e):
            print(f'Web configuration for \'{name}\' not found')
        return
    return response


def get_cup_id(name: str) -> Union[str | None]:
    ids = []
    paginator = cognito_client.get_paginator('list_user_pools')
    response = paginator.paginate(
        PaginationConfig={
            'MaxItems': 60,
            'PageSize': 10
        }
    )
    for page in response:
        ids.extend(
            [user_pool['Id'] for user_pool in page['UserPools'] if
             user_pool['Name'] == name]
        )
    next_token = response.resume_token
    while next_token:
        response = paginator.paginate(
            PaginationConfig={
                'MaxItems': 60,
                'PageSize': 10,
                'StartingToken': next_token
            }
        )
        for page in response:
            ids.extend(
                [user_pool['Id'] for user_pool in page['UserPools'] if
                 user_pool['Name'] == name]
            )
        next_token = response.resume_token

    if len(ids) == 1:
        return ids[0]
    if len(ids) > 1:
        print(
            f'Cognito User Pool can\'t be identified unambiguously because '
            f'there is more than one resource with the name \'{name}\'')
    else:
        print(f'Cognito User Pool \'{name}\' not found')
    return


def describe_swagger_ui(name: str, deployment_bucket: str, bundle_name: str,
                        deploy_name: str) -> Union[dict | None]:
    success_deploy_key = \
        f'{bundle_name}/{DEPLOY_OUTPUT_DIR}/{deploy_name}.json'
    failed_deploy_key = \
        f'{bundle_name}/{DEPLOY_OUTPUT_DIR}/{deploy_name}_failed.json'
    deploy_output = (
            get_s3_bucket_object(deployment_bucket, success_deploy_key) or
            get_s3_bucket_object(deployment_bucket, failed_deploy_key) or {})

    description = {}
    for arn, meta in deploy_output.items():
        if 'aws-syndicate' in arn and name in arn:
            target_bucket = deep_get(meta, ['resource_meta', 'target_bucket'])
            if target_bucket:
                description['target_bucket'] = target_bucket
            website_hosting = deep_get(meta,
                                       ['description', 'website_hosting'])
            if website_hosting:
                description['website_hosting'] = website_hosting
            break
    if not description:
        print(f'SwaggerUI \'{name}\' not found')
        return
    return description


def delete_s3_object(bucket_name: str, file_path: str):
    try:
        response = s3_client.delete_object(Bucket=bucket_name,
                                           Key=file_path)
    except ClientError as e:
        print(e)
        return
    return response


def delete_s3_folder(bucket_name: str, folder_path: str):
    objects_to_delete = s3_client.list_objects_v2(Bucket=bucket_name,
                                                  Prefix=folder_path)
    if 'Contents' in objects_to_delete:
        for obj in objects_to_delete['Contents']:
            print(f"Deleting object {obj['Key']}...")
            delete_s3_object(bucket_name=bucket_name, file_path=obj['Key'])
    else:
        print(f'Folder {folder_path} is already empty or does not exist')
