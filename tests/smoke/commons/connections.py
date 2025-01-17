import json
from datetime import datetime
from typing import Union
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from smoke.commons.constants import DEPLOY_OUTPUT_DIR
from smoke.commons.utils import deep_get, transform_tags

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
dynamodb_client = boto3.client('dynamodb', config=config)
dynamodb = boto3.resource('dynamodb', config=config)
eventbridge_client = boto3.client('events', config=config)
s3_client = boto3.client('s3', config=config)
cognito_client = boto3.client('cognito-idp', config=config)
iam_client = boto3.client('iam', config=config)
sts_client = boto3.client('sts', config=config)
cloudtrail_client = boto3.client('cloudtrail', config=config)
appsync_client = boto3.client('appsync', config=config)
batch_client = boto3.client('batch', config=config)

ACCOUNT_ID = sts_client.get_caller_identity()['Account']
REGION = sts_client.meta.region_name


def get_s3_bucket_file_content(bucket_name, file_key):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    except s3_client.exceptions.NoSuchKey:
        print(f'Not found key {file_key} in the bucket {bucket_name}')
        return '{}'
    return file_obj["Body"].read()


def get_s3_bucket_object(bucket_name, file_key):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    except s3_client.exceptions.NoSuchKey:
        print(f'Not found key {file_key} in the bucket {bucket_name}')
        return
    return file_obj


def if_s3_object_modified(bucket_name, file_key, modified_since: datetime):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key,
                                        IfModifiedSince=modified_since)
    except s3_client.exceptions.NoSuchKey:
        print(f'Not found key {file_key} in the bucket {bucket_name}')
        return
    except ClientError as e:
        if 'Not Modified' in str(e):
            print(f'File {file_key} was not modified')
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
    except iam_client.exceptions.NoSuchEntityException:
        print(f'Policy \'{policy_name}\' not found')
        return
    return response


def get_iam_role(role_name: str) -> Union[dict | None]:
    try:
        response = iam_client.get_role(RoleName=role_name)['Role']
    except iam_client.exceptions.NoSuchEntityException:
        print(f'Role \'{role_name}\' not found')
        return
    return response or {}


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
    return response.get('LayerVersions')


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
        print(f'Topic \'{name}\' not found')
        return
    return response


def get_dynamodb_table_description(name: str) -> Union[dict | None]:
    try:
        result = dynamodb_client.describe_table(TableName=name)
    except dynamodb_client.exceptions.ResourceNotFoundException:
        print(f'Table \'{name}\' not found')
        return
    return result.get('Table')


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
    except ClientError as e:
        if 'Not Found' in str(e):
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


def get_appsync_id(name: str) -> Union[str | None]:
    ids = []
    # todo change list_graphql_apis to list_apis in higher boto3 version
    paginator = appsync_client.get_paginator('list_graphql_apis')
    response = paginator.paginate(
        PaginationConfig={
            'MaxItems': 60,
            'PageSize': 10
        }
    )
    for page in response:
        ids.extend(
            [appsync['apiId'] for appsync in page['graphqlApis'] if
             appsync['name'] == name]
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
                [user_pool['apiId'] for user_pool in page['UserPools'] if
                 user_pool['Name'] == name]
            )
        next_token = response.resume_token

    if len(ids) == 1:
        return ids[0]
    if len(ids) > 1:
        print(
            f'Appsync can\'t be identified unambiguously because '
            f'there is more than one resource with the name \'{name}\'')
    else:
        print(f'Appsync \'{name}\' not found')


def describe_swagger_ui(name: str, deployment_bucket: str, bundle_path: str,
                        deploy_name: str) -> Union[dict | None]:
    success_deploy_key = \
        f'{bundle_path}/{DEPLOY_OUTPUT_DIR}/{deploy_name}.json'
    failed_deploy_key = \
        f'{bundle_path}/{DEPLOY_OUTPUT_DIR}/{deploy_name}_failed.json'
    deploy_output = (
            get_s3_bucket_file_content(deployment_bucket,
                                       success_deploy_key) or
            get_s3_bucket_file_content(deployment_bucket,
                                       failed_deploy_key) or {})
    deploy_output_json = json.loads(deploy_output)

    description = {}
    for arn, meta in deploy_output_json.items():
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


# ------- Get tags -----------

def list_role_tags(name: str, tag_keys: list = None):
    try:
        response = iam_client.list_role_tags(RoleName=name)
    except iam_client.exceptions.NoSuchEntityException:
        print(f'Role \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('Tags'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_policy_tags(name: str, tag_keys: list = None):
    try:
        response = iam_client.list_policy_tags(
            PolicyArn=f'arn:aws:iam::{ACCOUNT_ID}:policy/{name}')
    except iam_client.exceptions.NoSuchEntityException:
        print(f'Policy \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('Tags'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_lambda_tags(name, tag_keys: list = None):
    lambda_arn = f'arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{name}'
    try:
        response = lambda_client.list_tags(Resource=lambda_arn)
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f'Lambda \'{name}\' not found')
        return {}

    response_tags = response.get('Tags')
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_sns_topic_tags(name: str, tag_keys: list = None):
    topic_arn = f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:{name}'
    try:
        response = sns_client.list_tags_for_resource(ResourceArn=topic_arn)
    except sns_client.exceptions.NotFoundException:
        print(f'Topic \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('Tags'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_sqs_queue_tags(name: str, tag_keys: list = None):
    url = get_sqs_queue_url(name)
    if not url:
        return {}
    try:
        response = sqs_client.list_queue_tags(QueueUrl=url)
    except sqs_client.exceptions.QueueDoesNotExist:
        print(f'Queue \'{name}\' not found')
        return {}

    response_tags = response.get('Tags')
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_dynamodb_tags(name: str, tag_keys: list = None) -> Union[dict | None]:
    arn = f'arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/{name}'

    try:
        response = dynamodb_client.list_tags_of_resource(ResourceArn=arn)
    except dynamodb_client.exceptions.ResourceNotFoundException:
        print(f'Table \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('Tags'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_event_bridge_rule_tags(name: str,
                                tag_keys: list = None) -> Union[dict | None]:
    arn = f'arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/{name}'
    try:
        response = eventbridge_client.list_tags_for_resource(ResourceARN=arn)
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f'Rule \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('Tags'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_api_gateway_tags(name: str,
                          tag_keys: list = None) -> Union[dict | None]:
    response_tags = {}
    try:
        paginator = api_gw_client.get_paginator('get_rest_apis')
        for response in paginator.paginate():
            for api in response['items']:
                if api['name'] == name:
                    response_tags = api['tags']
    except api_gw_client.exceptions.ResourceNotFoundException:
        print(f'API Gateway \'{name}\' not found')

    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_s3_bucket_tags(name: str,
                        tag_keys: list = None) -> Union[dict | None]:
    try:
        response = s3_client.get_bucket_tagging(Bucket=name)
    except ClientError as error:
        if error.response['Error']['Code'] == 'NoSuchTagSet':
            print(f'No tags for S3 bucket \'{name}\'')
        return {}
    except s3_client.exceptions.NoSuchBucket:
        print(f'S3 bucket \'{name}\' not found')
        return {}

    response_tags = transform_tags(response.get('TagSet'))
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_cognito_tags(name: str, tag_keys: list = None) -> Union[dict | None]:
    cup_id = get_cup_id(name)
    arn = f'arn:aws:cognito-idp:{REGION}:{ACCOUNT_ID}:userpool/{cup_id}'

    try:
        response = cognito_client.list_tags_for_resource(ResourceArn=arn)
    except cognito_client.exceptions.ResourceNotFoundException:
        print(f'Cognito User Pool \'{name}\' not found')
        return {}

    response_tags = response.get('Tags')
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_appsync_tags(name: str, tag_keys: list = None) -> Union[dict | None]:
    cup_id = get_appsync_id(name)
    arn = f'arn:aws:appsync:{REGION}:{ACCOUNT_ID}:apis/{cup_id}'

    try:
        response = appsync_client.list_tags_for_resource(resourceArn=arn)
    except appsync_client.exceptions.NotFoundException:
        print(f'Appsync \'{name}\' not found')
        return {}

    response_tags = response.get('tags')
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def list_batch_tags(resource_arn: str, tag_keys: list = None) \
        -> Union[dict | None]:
    try:
        response = batch_client.list_tags_for_resource(
            resourceArn=resource_arn)
    except appsync_client.exceptions.NotFoundException:
        print(f'Batch resource with arn \'{resource_arn}\' not found')
        return {}

    response_tags = response.get('tags')
    if not tag_keys:
        return response_tags
    else:
        result = {}
        for tag in tag_keys:
            if tag in response_tags:
                result[tag] = response_tags[tag]
        return result


def get_lambda_event_source_mappings(name):
    result = []
    paginator = lambda_client.get_paginator('list_event_source_mappings')
    for response in paginator.paginate(FunctionName=name):
        result.extend(response.get('EventSourceMappings'))

    return result


def get_event_bridge_rule_targets(rule_name: str) -> list:
    result = []
    try:
        paginator = eventbridge_client.get_paginator('list_targets_by_rule')
        for response in paginator.paginate(Rule=rule_name):
            result.extend(response.get('Targets'))
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f'Rule \'{rule_name}\' not found')
        return []

    return result


def get_sns_topic_subscriptions(topic_arn: str) -> list:
    result = []
    try:
        paginator = sns_client.get_paginator('list_subscriptions_by_topic')
        for response in paginator.paginate(TopicArn=topic_arn):
            result.extend(response.get('Subscriptions'))
    except sns_client.exceptions.NotFoundException:
        print(f'Topic \'{topic_arn}\' not found')
        return []

    return result


def get_lambda_envs(lambda_name: str, qualifier: str = None):
    params = {
        'FunctionName': lambda_name
    }
    if qualifier:
        params['Qualifier'] = qualifier

    try:
        result = lambda_client.get_function_configuration(**params)
        return result.get('Environment', {})
    except lambda_client.exceptions.ResourceNotFoundException:
        return {}


def get_cloudtrail_event(event_name: str, event_value: str,
                         start_time: datetime = None,
                         end_time: datetime = None):
    params = {
        'LookupAttributes': [
            {
                'AttributeKey': event_name,
                'AttributeValue': event_value
            }
        ]
    }
    if start_time:
        params['StartTime'] = params
    if end_time:
        params['EndTime'] = end_time
    response = cloudtrail_client.lookup_events(**params)
    return response.get('Events', [])


def list_appsync_data_sources(api_id: str):
    result = []
    try:
        paginator = appsync_client.get_paginator('list_data_sources')
        for response in paginator.paginate(apiId=api_id):
            result.extend(response.get('dataSources'))
    except appsync_client.exceptions.NotFoundException:
        print(f'Appsync API \'{api_id}\' not found')
        return []

    return result


def list_appsync_resolvers(api_id: str, type_name: str):
    result = []
    try:
        paginator = appsync_client.get_paginator('list_resolvers')
        for response in paginator.paginate(apiId=api_id, typeName=type_name):
            result.extend(response.get('resolvers'))
    except appsync_client.exceptions.NotFoundException:
        print(f'Appsync API \'{api_id}\' with type name {type_name} not found')
        return []

    return result


def list_appsync_functions(api_id: str) -> list:
    result = []
    try:
        paginator = appsync_client.get_paginator('list_functions')
        for response in paginator.paginate(apiId=api_id):
            result.extend(response.get('functions'))
    except appsync_client.exceptions.NotFoundException:
        print(f'Appsync API \'{api_id}\' not found')
        return []

    return result


def get_batch_comp_env(name: str):
    arns = []
    paginator = batch_client.get_paginator('describe_compute_environments')
    for response in paginator.paginate(computeEnvironments=[name]):
        for env in response.get('computeEnvironments'):
            if env['computeEnvironmentName'] == name:
                arns.append(env['computeEnvironmentArn'])

    if len(arns) == 1:
        return arns[0]
    if len(arns) > 1:
        print(
            f'Batch compute environment can\'t be identified unambiguously '
            f'because there is more than one resource with the name \'{name}\''
        )
    else:
        print(f'Batch compute environment \'{name}\' not found')
    return


def get_batch_job_queue(name: str):
    arns = []
    paginator = batch_client.get_paginator('describe_job_queues')
    for response in paginator.paginate(jobQueues=[name]):
        for env in response.get('jobQueues'):
            if env['jobQueueName'] == name:
                arns.append(env['jobQueueArn'])

    if len(arns) == 1:
        return arns[0]
    if len(arns) > 1:
        print(
            f'Batch job queue can\'t be identified unambiguously '
            f'because there is more than one resource with the name \'{name}\''
        )
    else:
        print(f'Batch job queue \'{name}\' not found')
    return


def get_batch_job_definition(name: str):
    arns = []
    paginator = batch_client.get_paginator('describe_job_definitions')
    for response in paginator.paginate(jobDefinitionName=name):
        for env in response.get('jobDefinitions'):
            if env['jobDefinitionName'] == name and env['status'] == 'ACTIVE':
                arns.append(env['jobDefinitionArn'])

    if len(arns) == 1:
        return arns[0]
    if len(arns) > 1:
        print(
            f'Batch job definitions can\'t be identified unambiguously '
            f'because there is more than one resource with the name \'{name}\''
        )
    else:
        print(f'Batch job definitions \'{name}\' not found')
    return
