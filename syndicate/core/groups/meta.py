import os
import json

import click
from syndicate.core.generators.deployment_resources import \
    (S3Generator, DynamoDBGenerator, ApiGatewayGenerator, IAMPolicyGenerator,
     IAMRoleGenerator)
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import OrderedGroup, OptionRequiredIf
from syndicate.core.helper import check_bundle_bucket_name
from syndicate.core.helper import resolve_project_path, timeit
from syndicate.core.helper import check_valid_region

GENERATE_META_GROUP_NAME = 'meta'

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


@meta.command(name='dynamodb_table')
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
@click.option('--sort_key_type', type=click.Choice(['S', 'N', 'B']),
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
def dynamodb_table(ctx, **kwargs):
    """Generates dynamoDB deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGenerator(**kwargs)
    if generator.write_deployment_resource():
        click.echo(f"Table '{kwargs['resource_name']}' was "
                   f"added successfully!")


@meta.command(name='s3_bucket')
@click.option('-n', '--resource_name', required=True, type=str,
              help="S3 bucket name", callback=check_bundle_bucket_name)
@click.option('--location', type=str, callback=check_valid_region,
              help="The region where the bucket is created, the default value"
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
    if generator.write_deployment_resource():
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
    if generator.write_deployment_resource():
        click.echo(f"Api gateway '{kwargs['resource_name']}' was "
                   f"added successfully")

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
    if generator.write_deployment_resource():
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
    if generator.write_deployment_resource():
        click.echo(f"Iam role '{kwargs['resource_name']}' was "
                   f"added successfully")
