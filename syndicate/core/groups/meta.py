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
@click.option('--enable_cors', type=bool, help="Enables CORS on the resource"
                                               "method")
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
@click.pass_context
@timeit()
def api_gateway_resource_method(ctx, **kwargs):
    """Adds a method to existing api gateway resource"""
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


def _generate(generator: BaseConfigurationGenerator):
    """Just some common actions for this module are gathered in here"""
    try:
        generator.write()
    except ValueError as e:
        raise click.BadParameter(e)
    except RuntimeError as e:
        raise click.Abort(e)
