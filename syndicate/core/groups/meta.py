import os

import click
from syndicate.core.generators.deployment_resources import (S3Generator,
                                                            DynamoDBGenerator)
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import OrderedGroup
from syndicate.core.helper import check_bundle_bucket_name
from syndicate.core.helper import resolve_project_path, timeit

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
@click.pass_context
@timeit()
def s3_bucket(ctx, **kwargs):
    """Generates s3 bucket deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = S3Generator(**kwargs)
    if generator.write_deployment_resource():
        click.echo(f"S3 bucket {kwargs['resource_name']} was "
                   f"added successfully!")
