import os
import json

import click
from syndicate.core.generators.deployment_resources import *
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import OrderedGroup, OptionRequiredIf
from syndicate.core.helper import check_bundle_bucket_name
from syndicate.core.helper import resolve_project_path, timeit
from syndicate.core.helper import ValidRegionParamType

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


@meta.command(name='dynamodb')
@click.option('-n', '--resource_name', required=True, type=str,
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
@click.pass_context
@timeit()
def dynamodb(ctx, **kwargs):
    """Generates dynamoDB deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Table '{kwargs['resource_name']}' was added successfully!")


@meta.command(name='dynamodb_global_index')
@click.option('-n', '--table_name', required=True, type=str,
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
@click.pass_context
@timeit()
def dynamodb_global_index(ctx, **kwargs):
    """Adds dynamodb global index to existing dynamodb table"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGlobalIndexGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Global index '{kwargs['name']}' was added successfully")


@meta.command(name='dynamodb_autoscaling')
@click.option('-n', '--table_name', type=str, required=True,
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
@click.option('-n', '--resource_name', required=True, type=str,
              help="S3 bucket name", callback=check_bundle_bucket_name)
@click.option('--location', type=ValidRegionParamType(),
              help="The region where the bucket is created, the default value "
                   "is the region set in syndicate config")
@click.option('--acl', type=click.Choice(['private', 'public-read',
                                          'public-read-write',
                                          'authenticated-read']),
              help="The channel ACL to be applied to the bucket. If not "
                   "specified, sets the default value to 'private'")
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
@click.option('-n', '--resource_name', required=True, type=str,
              help="Api gateway name")
@click.option('--deploy_stage', required=True, type=str,
              help="The stage to deploy the API")
@click.option('--minimum_compression_size',
              type=click.IntRange(min=0, max=10*1024*1024),
              help="Compression size for api gateway. If not specified, "
                   "compression will be disabled")
@click.pass_context
@timeit()
def api_gateway(ctx, **kwargs):
    """Generates api gateway deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Api gateway '{kwargs['resource_name']}' was "
               f"added successfully")


@meta.command(name='api_gateway_resource')
@click.option('-n', '--api_name', required=True, type=str,
              help="Api gateway name to add index to")
@click.option('--path', required=True, type=click.Path(readable=False),
              help="Resource path to create")
@click.option('--enable_cors', type=bool,
              help="Enables CORS on the resourcemethod. If not specified, sets"
                   "the default value to False")
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
@click.option('-n', '--api_name', required=True, type=str,
              help="Api gateway name to add index to")
@click.option('--path', required=True, type=click.Path(readable=False),
              help="Resource path to create")
@click.option('--method', required=True,
              type=click.Choice(['POST', 'GET', 'DELETE', 'PUT', 'HEAD',
                                 'PATCH', 'ANY']),
              help="Resource method to add")
@click.option('--integration_type', type=str,
              help="The resource which the method is connected to: "
                   "[lambda|mock|http|mock]. If not specified, sets the default"
                   "value to 'mock'")
@click.option('--lambda_name', type=str, help="Lambda name. Required if "
                                              "integration type is lambda")
@click.option('--lambda_region', type=ValidRegionParamType(),
              help="The region where the lambda is located. If not specified, "
                   "sets the default value from syndicate config")
@click.option('--authorization_type',
              type=click.Choice(["AWS_IAM", "CUSTOM", "COGNITO_USER_POOLS"]),
              help="The method's authorization type. If not specified, sets "
                   "the default value to 'NONE'")
@click.option('--api_key_required', type=bool,
              help="Specifies whether the method requires a valid API key. "
                   "If not specified, the default value is set to False")
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
@click.option('-n', '--resource_name', required=True, type=str,
              help='IAM policy name')
@click.option('--policy_content', help='The path to JSON file with IAM policy '
                                       'content. If not specified, template '
                                       'value will be set',
              type=click.File(mode='r'))
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
@click.option('-n', '--resource_name', required=True, type=str,
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
@click.option('-n', '--resource_name', type=str, required=True,
              help="Kinesis stream name")
@click.option('--shard_count', type=int, required=True,
              help="Number of shards that the stream uses")
@click.pass_context
@timeit()
def kinesis_stream(ctx, **kwargs):
    """Generates kinesis stream deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = KinesisStreamGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Kinesis stream '{kwargs['resource_name']}' was"
               f"added successfully")


@meta.command(name='sns_topic')
@click.option('-n', '--resource_name', type=str, required=True,
              help="SNS topic name")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              required=True, help="Where the topic should be deployed")
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
@click.option('-n', '--resource_name', type=str, required=True,
              help="Step function activity name")
@click.pass_context
@timeit()
def step_function_activity(ctx, **kwargs):
    """Generates step function activity deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = StepFunctionActivityGenerator(**kwargs)
    _generate(generator)
    click.echo(f"Step function activity '{kwargs['resource_name']}' was"
               f"added successfully")


@meta.command(name='ec2_instance')
@click.option('-n', '--resource_name', type=str, required=True,
              help="Instance name")
@click.option('--key_name', type=str, required=True,
             help="SHH key to access the instance")
@click.option('--image_id', type=str, required=True,
             help="Image id to create the instance from")
@click.option('--instance_type', type=str,
             help="Instance type")
@click.option('--disable_api_termination', type=bool,
              help="Api termination protection")
@click.option('--security_group_ids', type=str, multiple=True,
              help="Security group ids")
@click.option('--security_group_names', type=str, multiple=True,
              help="Security group ids")  # ???
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
@click.pass_context
@timeit()
def ec2_instance(ctx, **kwargs):
    """Generates ec2 instance deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EC2InstanceGenerator(**kwargs)
    _generate(generator)
    click.echo(f"EC2 instance '{kwargs['resource_name']}' was added"
               f"successfully")


@meta.command(name='sqs_queue')
@click.option('-n', '--resource_name', type=str, required=True,
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
@click.pass_context
@timeit()
def sqs_queue(ctx, **kwargs):
    """Generates sqs queue deployment deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SQSQueueGenerator(**kwargs)
    _generate(generator)
    click.echo(f"SQS queue '{kwargs['resource_name']}' was added "
               f"successfully")


def _generate(generator: BaseConfigurationGenerator):
    """Just some common actions for this module are gathered in here"""
    try:
        generator.write()
    except ValueError as e:
        raise click.BadParameter(e)
    except RuntimeError as e:
        raise click.Abort(e)
