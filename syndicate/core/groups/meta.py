import json
import os
from functools import partial

import click

from syndicate.core.constants import S3_BUCKET_ACL_LIST, \
    API_GW_AUTHORIZER_TYPES, CUSTOM_AUTHORIZER_KEY, \
    EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS
from syndicate.core.generators.deployment_resources import *
from syndicate.core.generators.deployment_resources.api_gateway_generator import \
    ApiGatewayAuthorizerGenerator
from syndicate.core.generators.deployment_resources.ec2_launch_template_generator import \
    EC2LaunchTemplateGenerator
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import OrderedGroup, OptionRequiredIf, \
    validate_incompatible_options, validate_authorizer_name_option, \
    verbose_option
from syndicate.core.helper import ValidRegionParamType
from syndicate.core.helper import check_bundle_bucket_name
from syndicate.core.helper import resolve_project_path, timeit

GENERATE_META_GROUP_NAME = 'meta'
dynamodb_type_param = click.Choice(['S', 'N', 'B'])


@click.group(name=GENERATE_META_GROUP_NAME, cls=OrderedGroup)
@click.option('--project_path', nargs=1,
              help="Path to the project folder. Default value: the one "
                   "from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@click.pass_context
def meta(ctx, project_path):
    """Generates deployment resources templates"""
    if not os.access(project_path, os.F_OK):
        click.echo(f"The provided path {project_path} doesn't exist")
        return
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        click.echo(f"Incorrect permissions for the provided path "
                   f"'{project_path}'")
        return
    ctx.ensure_object(dict)
    ctx.obj[PROJECT_PATH_PARAM] = project_path


@meta.command(name='dax_cluster')
@click.option('--resource_name', required=True, type=str,
              help="Dax cluster name")
@click.option('--node_type', required=True, type=str,
              help="The node type for the nodes in the cluster")
@click.option('--iam_role_name', required=True, type=str,
              help="Role name to access DynamoDB tables")
@click.option('--subnet_group_name', required=True, type=str,
              help='The name of the subnet group to be used for the '
                   'replication group')
@click.option('--subnet_ids', type=str, multiple=True,
              help='Subnet ids to create a subnet group from. Don\'t specify '
                   'in case of using existing subnet group')
@click.option('--cluster_endpoint_encryption_type',
              type=click.Choice(['NONE', 'TLS']), default='TLS',
              help='The encryption type of the cluster\'s endpoint. '
                   'The default value is \'TLS\'')
@click.option('--parameter_group_name', type=str,
              help='The parameter group to be associated with the DAX cluster')
@verbose_option
@click.pass_context
@timeit()
def dax_cluster(ctx, **kwargs):
    """Generated dax cluster deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DaxClusterGenerator(**kwargs)
    _generate(generator)
    click.echo(f'Dax cluster \'{kwargs["resource_name"]}\' was '
               f'successfully generated')


@meta.command(name='dynamodb')
@click.option('--resource_name', required=True, type=str,
              help="DynamoDB table name")
@click.option('--hash_key_name', required=True, type=str,
              help="DynamoDB table hash key")
@click.option('--hash_key_type', required=True,
              type=click.Choice(['S', 'N', 'B']),
              help="DynamoDB hash key type")
@click.option('--sort_key_name', type=str,
              help="DynamoDB sort key. If not specified, the table will have "
                   "only a hash key")
@click.option('--sort_key_type', type=dynamodb_type_param,
              cls=OptionRequiredIf, required_if='sort_key_name',
              help="Required if sort key name is specified")
@click.option('--read_capacity', type=int,
              help="The maximum number of strongly consistent reads that can"
                   "be performed per second. If not specified, sets the "
                   "default value to 1")
@click.option('--write_capacity', type=int,
              help="The maximum number of writing processes consumed per"
                   "second. If not specified, sets the default value to 1")
@verbose_option
@click.pass_context
@timeit()
def dynamodb(ctx, **kwargs):
    """Generates dynamoDB deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Table '{kwargs['resource_name']}' was added successfully!")


@meta.command(name='dynamodb_global_index')
@click.option('--table_name', required=True, type=str,
              help="DynamoDB table name to add index to")
@click.option('--name', required=True, type=str,
              help="Index name")
@click.option('--index_key_name', required=True, type=str,
              help="Index hash key")
@click.option('--index_key_type', required=True,
              type=dynamodb_type_param,
              help='Hash key index type')
@click.option('--index_sort_key_name', type=str,
              help='Index sort key')
@click.option('--index_sort_key_type', type=dynamodb_type_param,
              cls=OptionRequiredIf, required_if='index_sort_key_name',
              help="Sort key type")
@verbose_option
@click.pass_context
@timeit()
def dynamodb_global_index(ctx, **kwargs):
    """Adds dynamodb global index to existing dynamodb table"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGlobalIndexGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Global index '{kwargs['name']}' was added successfully")


@meta.command(name='dynamodb_autoscaling')
@click.option('--table_name', type=str, required=True,
              help="DynamoDB table name to add autoscaling to")
@click.option('--policy_name', type=str, required=True,
              help="Autoscaling policy name")
@click.option('--min_capacity', type=click.IntRange(min=1),
              help="Minimum capacity level. If not specified, sets the default"
                   " value to 1")
@click.option('--max_capacity', type=click.IntRange(min=1),
              help="Maximum capacity level. If not specified, sets the default"
                   " value to 10")
@click.option('--target_utilization', type=click.IntRange(min=20, max=90),
              help="Target utilization in autoscaling. If not specified, sets "
                   "the default value to 70 %")
@click.option('--scale_in_cooldown', type=click.IntRange(min=0),
              help="Scaling policy value of in cooldown in seconds. Is not "
                   "specified, sets the default value to 60")
@click.option('--scale_out_cooldown', type=click.IntRange(min=0),
              help="Scaling policy value of out cooldown in seconds. Is not "
                   "specified, sets the default value to 60")
@click.option('--dimension', type=str,
              help="Autoscaling dimension. If not specified, sets the default"
                   "the default value to 'dynamodb:table:ReadCapacityUnits'")
@click.option('--role_name', type=str,
              help="The name of the role, which performs autoscaling. If not "
                   "specified, sets the value to default service linked role: "
                   "'AWSServiceRoleForApplicationAutoScaling_DynamoDBTable'")
@verbose_option
@click.pass_context
@timeit()
def dynamodb_autoscaling(ctx, **kwargs):
    """Adds autoscaling settings to existing dynamodb table"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBAutoscalingGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Autoscaling setting to table '{kwargs['table_name']}' was "
               f"added successfully")


@meta.command(name='s3_bucket')
@click.option('--resource_name', required=True, type=str,
              help="S3 bucket name", callback=check_bundle_bucket_name)
@click.option('--location', type=ValidRegionParamType(),
              help="The region where the bucket is created, the default value "
                   "is the region set in syndicate config")
@click.option('--acl', type=click.Choice(S3_BUCKET_ACL_LIST),
              help="The channel ACL to be applied to the bucket. If not "
                   "specified, sets the default value to 'private'")
@click.option('--block_public_acls', type=bool, required=False,
              is_eager=True,
              help='Specifies whether Amazon S3 should block public access '
                   'control lists (ACLs) for this bucket and objects in this '
                   'bucket. Default value is True')
@click.option('--ignore_public_acls', type=bool, required=False,
              is_eager=True,
              help='Specifies whether Amazon S3 should ignore public ACLs for '
                   'this bucket and objects in this bucket. Default value '
                   'is True')
@click.option('--block_public_policy', type=bool, required=False,
              is_eager=True,
              help='Specifies whether Amazon S3 should block public bucket '
                   'policies for this bucket. Default value is True')
@click.option('--restrict_public_buckets', type=bool, required=False,
              is_eager=True,
              help='Specifies whether Amazon S3 should restrict public bucket '
                   'policies for this bucket. Default value is True')
@click.option('--static_website_hosting', type=bool, required=False,
              callback=partial(validate_incompatible_options,
                               incompatible_options=['block_public_acls',
                                                     'ignore_public_acls',
                                                     'restrict_public_buckets',
                                                     'block_public_policy']),
              help='Specifies whether the S3 bucket should be configured for '
                   'static WEB site hosting. If specified public read access '
                   'will be configured for all S3 bucket objects! Default '
                   'value is False')
@verbose_option
@click.pass_context
@timeit()
def s3_bucket(ctx, **kwargs):
    """Generates s3 bucket deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = S3Generator(**kwargs)
    _generate(generator)
    click.echo(f"S3 bucket '{kwargs['resource_name']}' was "
               f"added successfully!")


@meta.command(name='api_gateway')
@click.option('--resource_name', required=True, type=str,
              help="Api gateway name")
@click.option('--deploy_stage', required=True, type=str,
              help="The stage to deploy the API")
@click.option('--minimum_compression_size',
              type=click.IntRange(min=0, max=10 * 1024 * 1024),
              help="Compression size for api gateway. If not specified, "
                   "compression will be disabled")
@verbose_option
@click.pass_context
@timeit()
def api_gateway(ctx, **kwargs):
    """Generates api gateway deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Api gateway '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='web_socket_api_gateway')
@click.option('--resource_name', required=True, type=str,
              help="Api gateway name")
@click.option('--deploy_stage', required=True, type=str,
              help="The stage to deploy the API")
@verbose_option
@click.pass_context
@timeit()
def web_socket_api_gateway(ctx, **kwargs):
    """Generates web socket api gateway deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = WebSocketApiGatewayGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Api gateway '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='api_gateway_authorizer')
@click.option('--api_name', required=True, type=str,
              help="Api gateway name to add index to")
@click.option('--name', required=True, type=str,
              help="Authorizer name")
@click.option('--type', type=click.Choice(API_GW_AUTHORIZER_TYPES),
              required=True, help="Authorizer type. 'TOKEN' for a Lambda "
                                  "function using a single authorization "
                                  "token submitted in a custom header, "
                                  "'REQUEST' for a Lambda function using "
                                  "incoming request parameters, and "
                                  "'COGNITO_USER_POOLS' for using an Amazon "
                                  "Cognito user pool")
@click.option('--provider_name', type=str, required=True,
              help="Identity provider name")
@verbose_option
@click.pass_context
@timeit()
def api_gateway_authorizer(ctx, **kwargs):
    """Adds authorizer to an existing api gateway"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayAuthorizerGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Authorizer '{kwargs['name']}' was added to API gateway "
               f"'{kwargs['api_name']}' successfully")


@meta.command(name='api_gateway_resource')
@click.option('--api_name', required=True, type=str,
              help="Api gateway name to add index to")
@click.option('--path', required=True, type=click.Path(readable=False),
              help="Resource path to create")
@click.option('--enable_cors', type=bool,
              help="Enables CORS on the resourcemethod. If not specified, sets"
                   "the default value to False")
@verbose_option
@click.pass_context
@timeit()
def api_gateway_resource(ctx, **kwargs):
    """Adds resource to existing api gateway"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayResourceGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Resource '{kwargs['path']}' was added to API gateway "
               f"'{kwargs['api_name']}' successfully")


@meta.command(name='api_gateway_resource_method')
@click.option('--api_name', required=True, type=str,
              help="Api gateway name to add index to")
@click.option('--path', required=True, type=click.Path(readable=False),
              help="Resource path to create")
@click.option('--method', required=True,
              type=click.Choice(['POST', 'GET', 'DELETE', 'PUT', 'HEAD',
                                 'PATCH', 'ANY']),
              help="Resource method to add")
@click.option('--integration_type', type=str,
              help="The resource which the method is connected to: "
                   "[lambda|service|http|mock]. If not specified, sets the "
                   "default value to 'mock'")
@click.option('--lambda_name', type=str, help="Lambda name. Required if "
                                              "integration type is lambda")
@click.option('--lambda_region', type=ValidRegionParamType(),
              help="The region where the lambda is located. If not specified, "
                   "sets the default value from syndicate config")
@click.option('--authorization_type', is_eager=True,
              type=click.Choice(["NONE", "AWS_IAM", CUSTOM_AUTHORIZER_KEY]),
              help="The method's authorization type. If not specified, sets "
                   "the default value to 'NONE'")
@click.option('--authorizer_name', type=str,
              callback=validate_authorizer_name_option,
              help="The method's authorizer name can be used only with "
                   "'--authorization_type' 'CUSTOM'")
@click.option('--api_key_required', type=bool,
              help="Specifies whether the method requires a valid API key. "
                   "If not specified, the default value is set to False")
@verbose_option
@click.pass_context
@timeit()
def api_gateway_resource_method(ctx, **kwargs):
    """Adds a method to existing api gateway resource"""

    if kwargs.get('integration_type') == 'lambda' \
            and not kwargs.get('lambda_name'):
        raise click.MissingParameter(
            "Lambda name is required if the integration type is 'lambda'",
            param_type='option', param_hint='lambda_name')

    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayResourceMethodGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Method '{kwargs['method']}' was added to API gateway "
               f"resource '{kwargs['path']}' successfully")


@meta.command(name='iam_policy')
@click.option('--resource_name', required=True, type=str,
              help='IAM policy name')
@click.option('--policy_content', help='The path to JSON file with IAM policy '
                                       'content. If not specified, template '
                                       'value will be set',
              type=click.File(mode='r'))
@verbose_option
@click.pass_context
@timeit()
def iam_policy(ctx, **kwargs):
    """Generates IAM policy deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    if kwargs['policy_content']:
        try:
            kwargs['policy_content'] = json.load(kwargs['policy_content'])
        except json.decoder.JSONDecodeError as e:
            raise click.BadParameter(str(e), param_hint='policy_content')
    generator = IAMPolicyGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Iam policy '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='iam_role')
@click.option('--resource_name', required=True, type=str,
              help="IAM role name")
@click.option('--principal_service', required=True, type=str,
              help="The service which will use the role")
@click.option("--predefined_policies", type=str, multiple=True,
              help="Managed IAM policies list")
@click.option("--custom_policies", type=str, multiple=True,
              help="Customer AWS policies names")
@click.option("--allowed_accounts", type=str, multiple=True,
              help="The list of accounts, which can assume the role")
@click.option("--external_id", type=str, help="External ID in role")
@click.option("--instance_profile", type=bool,
              help="If true, instance profile with role name is created")
@click.option('--permissions_boundary', type=str,
              help="The name or the ARN of permissions boundary policy to "
                   "attach to this role")
@verbose_option
@click.pass_context
@timeit()
def iam_role(ctx, **kwargs):
    """Generates IAM role deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = IAMRoleGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Iam role '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='kinesis_stream')
@click.option('--resource_name', type=str, required=True,
              help="Kinesis stream name")
@click.option('--shard_count', type=int, required=True,
              help="Number of shards that the stream uses")
@verbose_option
@click.pass_context
@timeit()
def kinesis_stream(ctx, **kwargs):
    """Generates kinesis stream deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = KinesisStreamGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Kinesis stream '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='sns_topic')
@click.option('--resource_name', type=str, required=True,
              help="SNS topic name")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              required=True, help="Where the topic should be deployed")
@verbose_option
@click.pass_context
@timeit()
def sns_topic(ctx, **kwargs):
    """Generates sns topic deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SNSTopicGenerator(**kwargs)
    _generate(generator)
    click.echo(f"SNS topic '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='step_function')
@click.option('--resource_name', type=str, required=True,
              help="Step function name")
@click.option('--iam_role', type=str, required=True,
              help="IAM role to use for this state machine")
@verbose_option
@click.pass_context
@timeit()
def step_function(ctx, **kwargs):
    """Generate step function deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = StepFunctionGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Step function '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='step_function_activity')
@click.option('--resource_name', type=str, required=True,
              help="Step function activity name")
@verbose_option
@click.pass_context
@timeit()
def step_function_activity(ctx, **kwargs):
    """Generates step function activity deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = StepFunctionActivityGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Step function activity '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='ec2_instance')
@click.option('--resource_name', type=str, required=True,
              help="Instance name")
@click.option('--key_name', type=str, required=True,
              help="SHH key to access the instance")
@click.option('--image_id', type=str, required=True,
              help="Image id to create the instance from")
@click.option('--instance_type', type=str,
              help="Instance type")
@click.option('--disable_api_termination', type=bool,
              help="Api termination protection. Default value is True")
@click.option('--security_group_ids', type=str, multiple=True,
              help="Security group ids")
@click.option('--security_group_names', type=str, multiple=True,
              help="Security group names")
@click.option('--availability_zone', type=str,
              help="Instance availability zone")
@click.option('--subnet_id', type=str, cls=OptionRequiredIf,
              required_if="availability_zone",
              help="Subnet ID (required if availability zone is set)")
@click.option('--userdata_file', type=str,
              help="File path to userdata (file relative pathname from the"
                   "directory which is set up in the env variable 'SDCT_CONF'")
@click.option('--iam_role', type=str,
              help="Instance IAM role")
@verbose_option
@click.pass_context
@timeit()
def ec2_instance(ctx, **kwargs):
    """Generates ec2 instance deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EC2InstanceGenerator(**kwargs)
    _generate(generator)
    click.echo(f"EC2 instance '{kwargs['resource_name']}' was added"
               f"successfully")


@meta.command(name='ec2_launch_template')
@click.option('--resource_name', type=str, required=True,
              help="Launch template name")
@click.option('--image_id', type=str, required=True,
              help="The ID of the AMI")
@click.option('--key_name', type=str,
              help="The name of the key pair")
@click.option('--instance_type', type=str,
              help="Instance type")
@click.option('--security_group_ids', type=str, multiple=True,
              help="Security group ids")
@click.option('--security_group_names', type=str, multiple=True,
              help="Security group names")
@click.option('--userdata_file', type=str,
              help="File path to userdata (can be specified as a relative "
                   "path to the project path)")
@click.option('--iam_role', type=str,
              help="Instance IAM role")
@click.option('--imds_version', type=click.Choice(
    EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS),
              help="IMDS version")
@click.option('--version_description', type=str,
              help="A description for the version of the launch template")
@verbose_option
@click.pass_context
@timeit()
def ec2_launch_template(ctx, **kwargs):
    """Generates ec2_launch_template deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EC2LaunchTemplateGenerator(**kwargs)
    _generate(generator)
    click.echo(f"ec2_launch_template '{kwargs['resource_name']}' was added "
               f"successfully")


@meta.command(name='sqs_queue')
@click.option('--resource_name', type=str, required=True,
              help="SQS queue name")
@click.option('--region', type=ValidRegionParamType(),
              help="The region where the queue is deployed. Default value is "
                   "the one from syndicate config")
@click.option('--fifo_queue', type=bool,
              help="If True, the queue is FIFO. Default value is False")
@click.option('--visibility_timeout', type=click.IntRange(min=0, max=43200),
              help="The visibility timeout for the queue. Default value is 30")
@click.option('--delay_seconds', type=click.IntRange(min=0, max=900),
              help="The length of time in seconds for which the delivery "
                   "of all the messages in the queue is delayed. Default "
                   "value is 0")
@click.option('--maximum_message_size',
              type=click.IntRange(min=1024, max=262144),
              help="The limit of how many bytes a message can contain before "
                   "Amazon SQS rejects it. Default value is 1024")
@click.option('--message_retention_period', type=click.IntRange(min=60,
                                                                max=1209600),
              help="The length of time in seconds for which Amazon SQS "
                   "retains a message. Default value is 60")
@click.option('--receive_message_wait_time_seconds',
              type=click.IntRange(min=0, max=20),
              help="The length of time in seconds for which a 'ReceiveMessage'"
                   " action waits for a message to arrive")
@click.option('--dead_letter_target_arn', type=str,
              help="Arn of a dead-letter queue Amazon SQS moves messages "
                   "after the value of maxReceiveCount is exceeded")
@click.option('--max_receive_count', type=click.IntRange(min=1, max=1000),
              help="The number of times a message is delivered to the source "
                   "queue before being moved to the dead-letter queue. "
                   "Required if 'dead_letter_target_arn' is specified",
              cls=OptionRequiredIf, required_if='dead_letter_target_arn')
@click.option('--kms_master_key_id', type=str,
              help="The id of an AWS-managed customer master key (CMK) for "
                   "Amazon SQS or a custom CMK")
@click.option('--kms_data_key_reuse_period_seconds',
              type=click.IntRange(min=60, max=86400),
              help="The length of time in seconds for which Amazon SQS can "
                   "reuse a data key to encrypt or decrypt messages before "
                   "calling AWS KMS again")
@click.option('--content_based_deduplication', type=bool,
              help="Enables content-based deduplication")
@verbose_option
@click.pass_context
@timeit()
def sqs_queue(ctx, **kwargs):
    """Generates sqs queue deployment deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SQSQueueGenerator(**kwargs)
    _generate(generator)
    click.echo(f"SQS queue '{kwargs['resource_name']}' was added "
               f"successfully")


@meta.command(name="sns_application")
@click.option('--resource_name', type=str, required=True,
              help="The name of the sns application")
@click.option('--platform', required=True,
              type=click.Choice(['GCM', 'ADM', 'APNS', 'APNS_SANDBOX']),
              help="SNS application platform")
@click.option('--region', type=ValidRegionParamType(),
              help="The region where the application is deployed. Default "
                   "value is the one from syndicate config")
@click.option('--attributes', type=(str, str), multiple=True,
              help="SNS application attributes")
@verbose_option
@click.pass_context
@timeit()
def sns_application(ctx, **kwargs):
    """Generates sns application deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SNSApplicationGenerator(**kwargs)
    _generate(generator)
    click.echo(f"SNS application '{kwargs['resource_name']}' was added "
               f"successfully")


@meta.command(name="cognito_user_pool")
@click.option('--resource_name', type=str, required=True,
              help="Cognito user pool name")
# @click.option('--region', type=ValidRegionParamType(), required=True,
#               help="The region where the user pool is created")
@click.option('--auto_verified_attributes',
              type=click.Choice(['phone_number', 'email']),
              help="The attributes to be auto-verified. "
                   "Default value is email", multiple=True)
@click.option('--sns_caller_arn', type=str,
              help="The arn of the IAM role in your account which Cognito "
                   "will use to send SMS messages. Required if 'phone_number' "
                   "in 'auto_verified_attributes' is specified")
@click.option('--username_attributes',
              type=click.Choice(['phone_number', 'email']),
              help="Specifies whether email addresses or phone numbers can "
                   "be specified as usernames when a user signs up. Default "
                   "value is email", multiple=True)
@click.option('--custom_attributes', type=(str, str), multiple=True,
              help="A list of custom attributes: (name type)")
@verbose_option
@click.pass_context
@timeit()
def cognito_user_pool(ctx, **kwargs):
    """Generates cognito user pool deployment resource template"""
    if 'phone_number' in kwargs['auto_verified_attributes'] \
            and not kwargs.get('sns_caller_arn'):
        raise click.MissingParameter("Sns caller IAM role arn is required when"
                                     " 'phone_number' is specified in "
                                     "'auto_verified_attributes'",
                                     param_type='option',
                                     param_hint='sns_caller_arn')

    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CognitoUserPoolGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Cognito user pool '{kwargs['resource_name']}' was added "
               f"successfully")


@meta.command(name="cognito_federated_pool")
@click.option('--resource_name', type=str, required=True,
              help="Cognito federated pool name")
@click.option('--auth_role', type=str,
              help="IAM role for authorized users")
@click.option('--unauth_role', type=str,
              help="IAM role for unauthorized users")
@click.option('--open_id_providers', type=str, multiple=True,
              help="A list of OpenID Connect providers")
@click.option('--provider_name', type=str,
              help="Developer provider name")
@verbose_option
@click.pass_context
@timeit()
def cognito_federated_pool(ctx, **kwargs):
    """Generates cognito federated pool deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CognitoFederatedPoolGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Cognito federated pool '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='batch_compenv')
@click.option('--resource_name', type=str, required=True,
              help="Batch compute environment name")
@click.option('--compute_environment_type',
              type=click.Choice(['MANAGED', 'UNMANAGED']),
              help="The type of compute environment. "
                   "Default value is 'MANAGED'")
@click.option('--allocation_strategy',
              type=click.Choice(['BEST_FIT', 'BEST_FIT_PROGRESSIVE',
                                 'SPOT_CAPACITY_OPTIMIZED']),
              help="The allocation strategy to use for the compute resource "
                   "if not enough instances of the best fitting instance type "
                   "can be allocated")
@click.option('--state', type=click.Choice(['ENABLED', 'DISABLED']),
              help="The state of compute environment")
@click.option('--service_role', type=str,
              help="The full Amazon Resource Name (ARN) of the IAM role that "
                   "allows Batch to make calls to other Amazon Web Services "
                   "services on your behalf. If not specified, role "
                   "'AWSBatchServiceRole' will be taken if it exists, if "
                   "doesn't it'll be created")
@click.option('--type',
              type=click.Choice(['EC2', 'SPOT', 'FARGATE', 'FARGATE_SPOT']),
              help="The type of compute environment. Default value is EC2")
@click.option('--minv_cpus', type=click.IntRange(min=0),
              help='The minimum number of Amazon EC2 vCPUs that an '
                   'environment should maintain. Default value is 0')
@click.option('--maxv_cpus', type=click.IntRange(min=1),
              help="The maximum number of Amazon EC2 vCPUs that a compute "
                   "environment can reach. Default value is 8")
@click.option('--desiredv_cpus', type=int,
              help="The desired number of Amazon EC2 vCPUS in the compute "
                   "environment. Default value is 1")
@click.option('--instance_types', type=str, multiple=True,
              help="The instances types that can be launched. Default value "
                   "is 'optimal'")
@click.option('--security_group_ids', type=str, multiple=True, required=True,
              help="The Amazon EC2 security groups associated with instances "
                   "launched in the compute environment")
@click.option('--subnets', type=str, multiple=True, required=True,
              help="The VPC subnets where the compute resources are launched")
@click.option('--instance_role', type=str,
              help="The Amazon ECS instance profile applied to Amazon EC2 "
                   "instances in a compute environment")
@verbose_option
@click.pass_context
@timeit()
def batch_compenv(ctx, **kwargs):
    """Generates batch compenv deployment resources template"""
    if kwargs.get('type') != 'FARGATE':
        if not kwargs.get('instance_role'):
            raise click.MissingParameter("'instance_role' is required if "
                                         "batch compenv type ISN'T 'FARGATE'",
                                         param_type='option',
                                         param_hint='instance_role')
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchCompenvGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Batch compute environment '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='batch_jobdef')
@click.option('--resource_name', type=str, required=True,
              help='Batch job definition name')
@click.option('--job_definition_type', required=True,
              type=click.Choice(['container', 'multinode']),
              help='The type of job definition')
@click.option('--image', type=str,
              help='The image used to start a container. '
                   'Default value is \'alpine\'')
@click.option('--job_role_arn', type=str,
              help='The ARN of the IAM role that the container can assume for '
                   'AWS permissions')
@verbose_option
@click.pass_context
@timeit()
def batch_jobdef(ctx, **kwargs):
    """Generates batch job definition deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchJobdefGenerator(**kwargs)
    _generate(generator)
    click.echo(f'Batch job definition \'{kwargs["resource_name"]}\' was '
               f'added successfully')


@meta.command(name="batch_jobqueue")
@click.option('--resource_name', type=str, required=True,
              help="Batch job queue name")
@click.option('--state', type=click.Choice(["ENABLED", "DISABLED"]),
              help="The state of the job queue. Default value is 'ENABLED'")
@click.option('--priority', type=int, help="The priority of the job queue. "
                                           "Default value is 1")
@click.option('--compute_environment_order', type=(int, str), multiple=True,
              help="The set of compute environments mapped to a job queue and "
                   "their order relative to each other. (order, compute_env)")
@verbose_option
@click.pass_context
@timeit()
def batch_jobqueue(ctx, **kwargs):
    """Generates batch job queue deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchJobqueueGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Batch job queue '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name="cloudwatch_alarm")
@click.option('--resource_name', type=str, required=True,
              help="Cloudwatch alarm name")
@click.option('--metric_name', type=str, required=True,
              help="The metric's name")
@click.option('--namespace', type=str, required=True,
              help="The namespace for the metric associated with the alarm")
@click.option('--description', type=str, help="The description for the alarm")
@click.option('--period', type=click.IntRange(min=1),
              help="The period in seconds over which the specified statistic "
                   "is applied. Valid values are 10, 30 and any multiple"
                   " of 60. Default value is 1200")
@click.option('--evaluation_periods', type=click.IntRange(min=1),
              help="The number of periods over which data is compared to the "
                   "specified threshold. Default value is 1")
@click.option('--threshold', type=float,
              help="The value to compare with the specified statistic. "
                   "Default value is 1.0")
@click.option('--comparison_operator',
              type=click.Choice(['GreaterThanOrEqualToThreshold',
                                 'GreaterThanThreshold',
                                 'LessThanThreshold',
                                 'LessThanOrEqualToThreshold',
                                 'LessThanLowerOrGreaterThanUpperThreshold',
                                 'LessThanLowerThreshold',
                                 'GreaterThanUpperThreshold']),
              help="An arithmetic operator to use when comparing the specified"
                   " statistic and threshold. The specified statistic value is"
                   " used as the first operand. Default value is "
                   "'GreaterThanOrEqualToThreshold'")
@click.option('--statistic', type=click.Choice(["SampleCount", "Average",
                                                'Sum', 'Minimum', 'Maximum']),
              help="The statistic for the metric associated with the alarm,"
                   "other than percentile. For percentile statistic use "
                   "'ExtendedStatistic'. Default value is 'SampleCount'")
@click.option('--sns_topics', type=str, multiple=True,
              help="The sns topics to execute when the alarm goes to an ALARM "
                   "state from any other state")
@click.option('--lambdas', type=str, multiple=True,
              help="The lambdas to execute when the alarm goes to an ALARM "
                   "state from any other state. Use `:` after lambda name to "
                   "specify alias or version")
@click.option('--ssm_response_plan', type=str, multiple=True,
              help="The response plan name to execute when the alarm goes to "
                   "an ALARM state from any other state")
@click.option('--evaluate_low_sample_count_percentile',
              type=click.Choice(["evaluate", "ignore"]),
              help="Only for percentiles-based alarms. Use 'ignore' and the "
                   "alarm state remains unchanged during periods with "
                   "insufficient data points for statistical significance. If "
                   "'evaluate' is specified (or parameter is omitted), the "
                   "alarm is always assessed and "
                   "may change state regardless of data point availability")
@click.option('--datapoints', type=click.IntRange(min=1),
              help="The number of datapoints that must be breaching to "
                   "trigger the alarm")
@verbose_option
@click.pass_context
@timeit()
def cloudwatch_alarm(ctx, **kwargs):
    """Generates Cloudwatch alarm deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CloudWatchAlarmGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Cloudwatch alarm '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name="cloudwatch_event_rule")
@click.option('--resource_name', type=str, required=True,
              help="Cloudwatch event rule name")
@click.option('--rule_type', required=True, help="Cloudwatch event rule type",
              type=click.Choice(['schedule', 'ec2', 'api_call']))
@click.option('--expression', type=str,
              help="Rule expression (cron schedule). Valuable only if "
                   "rule_type is 'schedule'")
@click.option('--aws_service', type=str,
              help="The name of AWS service which the rule listens to. "
                   "Required only if rule_type is 'api_call'")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              help="The region where the rule is deployed. Default value is "
                   "the one from syndicate config")
@verbose_option
@click.pass_context
@timeit()
def cloudwatch_event_rule(ctx, **kwargs):
    """Generates Cloudwatch event rule deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CloudwatchEventRuleGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Cloudwatch event rule '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name="eventbridge_rule")
@click.option('--resource_name', type=str, required=True,
              help="EventBridge rule name")
@click.option('--rule_type', required=True, help="EventBridge rule type",
              type=click.Choice(['schedule', 'ec2', 'api_call']))
@click.option('--expression', type=str,
              help="Rule expression (cron schedule). Valuable only if "
                   "rule_type is 'schedule'")
@click.option('--aws_service', type=str,
              help="The name of AWS service which the rule listens to. "
                   "Required only if rule_type is 'api_call'")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              help="The region where the rule is deployed. Default value is "
                   "the one from syndicate config")
@verbose_option
@click.pass_context
@timeit()
def eventbridge_rule(ctx, **kwargs):
    """Generates EventBridge rule deployment resources-template
    claiming compatibility with Cloudwatch event rule generator"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EventBridgeRuleGenerator(**kwargs)
    _generate(generator)
    click.echo(f"EventBridge rule '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name="documentdb_cluster")
@click.option('--resource_name', type=str, required=True,
              help="DocumentDB cluster name")
@click.option('--master_username', type=str, required=True,
              help="DocumentDB login ID for the master user")
@click.option('--master_password', type=str, required=True,
              help="The password for master user")
@click.option('--port', type=int,
              help="The port number on which the instances in the cluster "
                   "accept connections. Default value is 27017")
@click.option('--vpc_security_group_ids', type=str, multiple=True,
              help="A list of EC2 VPC security groups to associate with this "
                   "cluster. Is not specified, default security group is used")
@click.option('--availability_zones', type=str, multiple=True,
              help="A list of Amazon EC2 Availability Zones that instances in "
                   "the cluster can be created in. "
                   "If not specified default is used")
@verbose_option
@click.pass_context
@timeit()
def documentdb_cluster(ctx, **kwargs):
    """Generates documentdb cluster deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DocumentDBClusterGenerator(**kwargs)
    _generate(generator)
    click.echo(f"DocumentDB cluster '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name="documentdb_instance")
@click.option('--resource_name', type=str, required=True,
              help="DocumentDB instance name")
@click.option('--cluster_identifier', type=str, required=True,
              help="The identifier of the cluster that the instance will "
                   "belong to")
@click.option('--instance_class', type=str,
              help="The compute and memory capacity of the instance. Default "
                   "value is 'db.r5.large'")
@click.option('--availability_zone', type=str,
              help="The Amazon EC2 Availability Zone that the instance is "
                   "created in. If not specified a random zone it the "
                   "endpoint's region is set")
@verbose_option
@click.pass_context
@timeit()
def documentdb_instance(ctx, **kwargs):
    """Generates documentdb instance deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DocumentDBInstanceGenerator(**kwargs)
    _generate(generator)
    click.echo(f"DocumentDB instance '{kwargs['resource_name']}' was "
               f"added successfully")


def _generate(generator: BaseConfigurationGenerator):
    """Just some common actions for this module are gathered in here"""
    try:
        generator.write()
    except ValueError as e:
        raise click.BadParameter(e)
    except RuntimeError as e:
        raise click.Abort(e)
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")
