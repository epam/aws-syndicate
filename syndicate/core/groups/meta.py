import json
import os
from functools import partial

import click

from syndicate.core.generators.deployment_resources.rds_generator import \
    RDSDBClusterGenerator, RDSDBInstanceGenerator
from syndicate.exceptions import AbortedError,  SyndicateBaseError
from syndicate.commons.log_helper import get_user_logger
from syndicate.core.constants import (
    S3_BUCKET_ACL_LIST, API_GW_AUTHORIZER_TYPES, CUSTOM_AUTHORIZER_KEY,
    EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS, EC2_LT_RESOURCE_TAGS,
    FAILED_RETURN_CODE, OK_RETURN_CODE,
)
from syndicate.core.decorators import return_code_manager
from syndicate.core.generators.deployment_resources import *
from syndicate.core.generators.deployment_resources.api_gateway_generator import \
    ApiGatewayAuthorizerGenerator

from syndicate.core.generators.deployment_resources.ec2_launch_template_generator import \
    EC2LaunchTemplateGenerator
from syndicate.core.generators.deployment_resources.eventbridge_schedule import \
    EventBridgeScheduleGenerator
from syndicate.core.generators.deployment_resources.firehose_generator import \
    FirehoseGenerator
from syndicate.core.generators.lambda_function import PROJECT_PATH_PARAM
from syndicate.core.helper import (
    OptionRequiredIf, check_tags,
    validate_authorizer_name_option, verbose_option, validate_api_gw_path,
    DictParamType, DeepDictParamType, validate_incompatible_options,
    AliasedCommandsGroup, MultiWordOption, combine_option_classes,
)
from syndicate.core.helper import ValidRegionParamType
from syndicate.core.helper import validate_bucket_name
from syndicate.core.helper import resolve_project_path, timeit

GENERATE_META_GROUP_NAME = 'meta'
dynamodb_type_param = click.Choice(['S', 'N', 'B'])

RDS_INSTANCE_DB_CLUSTER_INCOMPATIBLE_OPTIONS = [
    'engine', 'engine-version', 'master-username', 'master-password',
    'database-name', 'port', 'vpc-security-group-ids', 'availability-zone']

OptionCombined = combine_option_classes(OptionRequiredIf, MultiWordOption)

USER_LOG = get_user_logger()


@click.group(name=GENERATE_META_GROUP_NAME, cls=AliasedCommandsGroup)
@return_code_manager
@click.option('--project-path', '-path',
              cls=MultiWordOption, nargs=1,
              help="Path to the project root directory. Default value: "
                   "the one from the current config if it exists. "
                   "Otherwise - the current working directory",
              callback=resolve_project_path)
@click.pass_context
def meta(ctx, project_path):
    """Generates deployment resources templates"""
    if not os.access(project_path, os.F_OK):
        USER_LOG.error(f"The provided path {project_path} doesn't exist")
        return FAILED_RETURN_CODE
    elif not os.access(project_path, os.W_OK) or not os.access(project_path,
                                                               os.X_OK):
        USER_LOG.error(f"Incorrect permissions for the provided path "
                       f"'{project_path}'")
        return FAILED_RETURN_CODE
    ctx.ensure_object(dict)
    ctx.obj[PROJECT_PATH_PARAM] = project_path
    return OK_RETURN_CODE


@meta.command(name='dax-cluster')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption,
              required=True, type=str, help="Dax cluster name")
@click.option('--node-type',
              cls=MultiWordOption,
              required=True, type=str,
              help="The node type for the nodes in the cluster")
@click.option('--iam-role-name',
              cls=MultiWordOption,
              required=True, type=str,
              help="Role name to access DynamoDB tables")
@click.option('--subnet-group-name',
              cls=MultiWordOption,
              required=True, type=str,
              help='The name of the subnet group to be used for the '
                   'replication group')
@click.option('--subnet-ids',
              cls=MultiWordOption, type=str, multiple=True,
              help='Subnet ids to create a subnet group from. Don\'t specify '
                   'in case of using existing subnet group')
@click.option('--cluster-endpoint-encryption-type',
              cls=MultiWordOption,
              type=click.Choice(['NONE', 'TLS']), default='TLS',
              help='The encryption type of the cluster\'s endpoint. '
                   'The default value is \'TLS\'')
@click.option('--parameter-group-name',
              cls=MultiWordOption, type=str,
              help='The parameter group to be associated with the DAX cluster')
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def dax_cluster(ctx, **kwargs):
    """Generated dax cluster deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DaxClusterGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f'Dax cluster \'{kwargs["resource_name"]}\' was '
                  f'successfully generated')
    return OK_RETURN_CODE


@meta.command(name='dynamodb')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help="DynamoDB table name")
@click.option('--hash-key-name',
              cls=MultiWordOption, required=True, type=str,
              help="DynamoDB table hash key")
@click.option('--hash-key-type',
              cls=MultiWordOption, required=True,
              type=click.Choice(['S', 'N', 'B']),
              help="DynamoDB hash key type")
@click.option('--sort-key-name',
              cls=MultiWordOption, type=str,
              help="DynamoDB sort key. If not specified, the table will have "
                   "only a hash key")
@click.option('--sort-key-type',
              type=dynamodb_type_param,
              cls=OptionCombined, required_if='sort-key-name',
              help="Required if sort key name is specified")
@click.option('--billing-mode',
              cls=MultiWordOption, required=True,
              type=click.Choice(['PROVISIONED', 'PAY_PER_REQUEST']),
              default='PAY_PER_REQUEST',
              help="Controls how you are charged for read and write "
                   "throughput")
@click.option('--read-capacity',
              cls=MultiWordOption, type=int,
              help="The maximum number of strongly consistent reads that can"
                   "be performed per second in PROVISIONED billing mode. "
                   "Maximum number of read request units in PAY_PER_REQUEST "
                   "billing mode. If not specified, sets the default value "
                   "to 1")
@click.option('--write-capacity',
              cls=MultiWordOption, type=int,
              help="The maximum number of writing processes consumed per"
                   "second in PROVISIONED billing mode. "
                   "Maximum number of write request units in PAY_PER_REQUEST "
                   "billing mode. If not specified, sets the default value "
                   "to 1")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def dynamodb(ctx, **kwargs):
    """Generates dynamoDB deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Table '{kwargs['resource_name']}' was added successfully!")
    return OK_RETURN_CODE


@meta.command(name='dynamodb-global-index')
@return_code_manager
@click.option('--table-name',
              cls=MultiWordOption, required=True, type=str,
              help="DynamoDB table name to add index to")
@click.option('--name', required=True, type=str,
              help="Index name")
@click.option('--index-key-name',
              cls=MultiWordOption, required=True, type=str,
              help="Index hash key")
@click.option('--index-key-type',
              cls=MultiWordOption, required=True,
              type=dynamodb_type_param,
              help='Hash key index type')
@click.option('--index-sort-key_name',
              cls=MultiWordOption, type=str,
              help='Index sort key')
@click.option('--index-sort-key-type',
              cls=OptionCombined, type=dynamodb_type_param,
              required_if='index-sort-key-name',
              help="Sort key type")
@verbose_option
@click.pass_context
@timeit()
def dynamodb_global_index(ctx, **kwargs):
    """Adds dynamodb global index to existing dynamodb table"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DynamoDBGlobalIndexGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Global index '{kwargs['name']}' was added successfully")
    return OK_RETURN_CODE


@meta.command(name='dynamodb-autoscaling')
@return_code_manager
@click.option('--table-name',
              cls=MultiWordOption, type=str, required=True,
              help="DynamoDB table name to add autoscaling to")
@click.option('--policy-name',
              cls=MultiWordOption, type=str, required=True,
              help="Autoscaling policy name")
@click.option('--min-capacity',
              cls=MultiWordOption, type=click.IntRange(min=1),
              help="Minimum capacity level. If not specified, sets the default"
                   " value to 1")
@click.option('--max-capacity',
              cls=MultiWordOption, type=click.IntRange(min=1),
              help="Maximum capacity level. If not specified, sets the default"
                   " value to 10")
@click.option('--target-utilization',
              cls=MultiWordOption,
              type=click.IntRange(min=20, max=90),
              help="Target utilization in autoscaling. If not specified, sets "
                   "the default value to 70 %")
@click.option('--scale-in-cooldown',
              cls=MultiWordOption, type=click.IntRange(min=0),
              help="Scaling policy value of in cooldown in seconds. Is not "
                   "specified, sets the default value to 60")
@click.option('--scale-out-cooldown',
              cls=MultiWordOption, type=click.IntRange(min=0),
              help="Scaling policy value of out cooldown in seconds. Is not "
                   "specified, sets the default value to 60")
@click.option('--dimension', type=str,
              help="Autoscaling dimension. If not specified, sets the default"
                   "value to 'dynamodb:table:ReadCapacityUnits'")
@click.option('--role-name',
              cls=MultiWordOption, type=str,
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
    USER_LOG.info(f"Autoscaling setting to table '{kwargs['table_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='s3-bucket')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help="S3 bucket name", callback=validate_bucket_name)
@click.option('--location', type=ValidRegionParamType(),
              help="The region where the bucket is created, the default value "
                   "is the region set in syndicate config")
@click.option('--acl', type=click.Choice(S3_BUCKET_ACL_LIST),
              help="The channel ACL to be applied to the bucket. If not "
                   "specified, sets the default value to 'private'")
@click.option('--block-public-acls',
              cls=MultiWordOption,
              type=bool, required=False, is_eager=True,
              help='Specifies whether Amazon S3 should block public access '
                   'control lists (ACLs) for this bucket and objects in this '
                   'bucket. Default value is True')
@click.option('--ignore-public-acls',
              cls=MultiWordOption,
              type=bool, required=False, is_eager=True,
              help='Specifies whether Amazon S3 should ignore public ACLs for '
                   'this bucket and objects in this bucket. Default value '
                   'is True')
@click.option('--block-public-policy',
              cls=MultiWordOption,
              type=bool, required=False, is_eager=True,
              help='Specifies whether Amazon S3 should block public bucket '
                   'policies for this bucket. Default value is True')
@click.option('--restrict-public-buckets',
              cls=MultiWordOption,
              type=bool, required=False, is_eager=True,
              help='Specifies whether Amazon S3 should restrict public bucket '
                   'policies for this bucket. Default value is True')
@click.option('--static-website-hosting',
              cls=MultiWordOption, type=bool, required=False,
              help='Specifies whether the S3 bucket should be configured for '
                   'static WEB site hosting. Default value is False')
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def s3_bucket(ctx, **kwargs):
    """Generates s3 bucket deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = S3Generator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"S3 bucket '{kwargs['resource_name']}' was "
                  f"added successfully!")
    return OK_RETURN_CODE


@meta.command(name='api-gateway')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help="Api gateway name")
@click.option('--deploy-stage',
              cls=MultiWordOption, required=True, type=str,
              help="The stage to deploy the API")
@click.option('--minimum-compression-size',
              cls=MultiWordOption,
              type=click.IntRange(min=0, max=10 * 1024 * 1024),
              help="Compression size for api gateway. If not specified, "
                   "compression will be disabled")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def api_gateway(ctx, **kwargs):
    """Generates api gateway deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Api gateway '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='web-socket-api-gateway')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help="Api gateway name")
@click.option('--deploy-stage',
              cls=MultiWordOption, required=True, type=str,
              help="The stage to deploy the API")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def web_socket_api_gateway(ctx, **kwargs):
    """Generates web socket api gateway deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = WebSocketApiGatewayGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Api gateway '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='api-gateway-authorizer')
@return_code_manager
@click.option('--api-name',
              cls=MultiWordOption, required=True, type=str,
              help="Api gateway name to add authorizer to")
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
@click.option('--provider-name',
              cls=MultiWordOption, type=str, required=True,
              help="Identity provider name")
@verbose_option
@click.pass_context
@timeit()
def api_gateway_authorizer(ctx, **kwargs):
    """Adds authorizer to an existing api gateway"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayAuthorizerGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Authorizer '{kwargs['name']}' was added to API gateway "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


@meta.command(name='api-gateway-resource')
@return_code_manager
@click.option('--api-name',
              cls=MultiWordOption, required=True, type=str,
              help="Api gateway name to add resource to")
@click.option('--path', required=True, callback=validate_api_gw_path,
              help="Resource path to create")
@click.option('--enable-cors',
              cls=MultiWordOption, type=bool,
              help="Enables CORS on the resource method. If not specified, "
                   "sets the default value to False")
@verbose_option
@click.pass_context
@timeit()
def api_gateway_resource(ctx, **kwargs):
    """Adds resource to existing api gateway"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = ApiGatewayResourceGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Resource '{kwargs['path']}' was added to API gateway "
                  f"'{kwargs['api_name']}' successfully")
    return OK_RETURN_CODE


@meta.command(name='api-gateway-resource-method')
@return_code_manager
@click.option('--api-name',
              cls=MultiWordOption, required=True, type=str,
              help="Api gateway name to add method to")
@click.option('--path', required=True, callback=validate_api_gw_path,
              help="Resource path to add method to")
@click.option('--method', required=True,
              type=click.Choice(['POST', 'GET', 'DELETE', 'PUT', 'HEAD',
                                 'PATCH', 'ANY']),
              help="Resource method to add")
@click.option('--integration-type',
              cls=MultiWordOption, type=str,
              help="The resource which the method is connected to: "
                   "[lambda|service|http|mock]. If not specified, sets the "
                   "default value to 'mock'")
@click.option('--lambda-name',
              cls=MultiWordOption, type=str,
              help="Lambda name. Required if integration type is lambda")
@click.option('--lambda-region',
              cls=MultiWordOption, type=ValidRegionParamType(),
              help="The region where the lambda is located. If not specified, "
                   "sets the default value from syndicate config")
@click.option('--authorization-type',
              cls=MultiWordOption, is_eager=True,
              type=click.Choice(["NONE", "AWS_IAM", CUSTOM_AUTHORIZER_KEY]),
              help="The method's authorization type. If not specified, sets "
                   "the default value to 'NONE'")
@click.option('--authorizer-name',
              cls=MultiWordOption, type=str,
              callback=validate_authorizer_name_option,
              help="The method's authorizer name can be used only with "
                   "'--authorization_type' 'CUSTOM'")
@click.option('--api-key-required',
              cls=MultiWordOption, type=bool,
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
    USER_LOG.info(f"Method '{kwargs['method']}' was added to API gateway "
                  f"resource '{kwargs['path']}' successfully")
    return OK_RETURN_CODE


@meta.command(name='iam-policy')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help='IAM policy name')
@click.option('--policy-content',
              cls=MultiWordOption,
              help='The path to JSON file with IAM policy content. '
                   'If not specified, template value will be set',
              type=click.File(mode='r'))
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
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
    USER_LOG.info(f"Iam policy '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='iam-role')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, required=True, type=str,
              help="IAM role name")
@click.option('--principal-service',
              cls=MultiWordOption, required=True, type=str,
              help="The service which will use the role")
@click.option('--predefined-policies',
              cls=MultiWordOption, type=str, multiple=True,
              help="Managed IAM policies list")
@click.option('--custom-policies',
              cls=MultiWordOption, type=str, multiple=True,
              help="Customer AWS policies names")
@click.option('--allowed-accounts',
              cls=MultiWordOption, type=str, multiple=True,
              help="The list of accounts, which can assume the role")
@click.option('--external-id',
              cls=MultiWordOption,
              type=str, help="External ID in role")
@click.option('--instance-profile',
              cls=MultiWordOption, type=bool,
              help="If true, instance profile with role name is created")
@click.option('--permissions-boundary',
              cls=MultiWordOption, type=str,
              help="The name or the ARN of permissions boundary policy to "
                   "attach to this role")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def iam_role(ctx, **kwargs):
    """Generates IAM role deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = IAMRoleGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Iam role '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='kinesis-stream')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Kinesis stream name")
@click.option('--shard-count',
              cls=MultiWordOption, type=int, required=True,
              help="Number of shards that the stream uses")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def kinesis_stream(ctx, **kwargs):
    """Generates kinesis stream deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = KinesisStreamGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Kinesis stream '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='sns-topic')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="SNS topic name")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              required=True, help="Where the topic should be deployed")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def sns_topic(ctx, **kwargs):
    """Generates sns topic deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SNSTopicGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"SNS topic '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='step-function')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Step function name")
@click.option('--iam-role',
              cls=MultiWordOption, type=str, required=True,
              help="IAM role to use for this state machine")
@click.option('--publish_version', type=bool, default=False,
              help="Defines whether to publish the step function version")
@click.option('--alias', type=str,
              help="Step function alias name")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def step_function(ctx, **kwargs):
    """Generate step function deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = StepFunctionGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Step function '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='step-function-activity')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Step function activity name")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def step_function_activity(ctx, **kwargs):
    """Generates step function activity deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = StepFunctionActivityGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Step function activity '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='ec2-instance')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Instance name")
@click.option('--key-name',
              cls=MultiWordOption, type=str, required=True,
              help="SSH key to access the instance")
@click.option('--image-id',
              cls=MultiWordOption, type=str, required=True,
              help="Image id to create the instance from")
@click.option('--instance-type',
              cls=MultiWordOption, type=str,
              help="Instance type. Default type: t2.micro")
@click.option('--disable-api-termination',
              cls=MultiWordOption, type=bool,
              help="Api termination protection. Default value is True")
@click.option('--security-group-ids',
              cls=MultiWordOption, type=str, multiple=True,
              help="Security group ids")
@click.option('--security-group-names',
              cls=MultiWordOption, type=str, multiple=True,
              help="Security group names")
@click.option('--availability-zone',
              cls=MultiWordOption, type=str,
              help="Instance availability zone")
@click.option('--subnet-id',
              type=str, cls=OptionCombined,
              required_if="availability-zone",
              help="Subnet ID (required if availability zone is set)")
@click.option('--userdata-file',
              cls=MultiWordOption, type=str,
              help="File path to userdata (file relative pathname from the"
                   "directory which is set up in the env variable 'SDCT_CONF'")
@click.option('--iam-role',
              cls=MultiWordOption, type=str,
              help="Instance IAM role")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def ec2_instance(ctx, **kwargs):
    """Generates ec2 instance deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EC2InstanceGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"EC2 instance '{kwargs['resource_name']}' was added"
                  f"successfully")
    return OK_RETURN_CODE


@meta.command(name='ec2-launch-template')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Launch template name")
@click.option('--image-id',
              cls=MultiWordOption, type=str, required=True,
              help="The ID of the AMI")
@click.option('--key-name',
              cls=MultiWordOption, type=str,
              help="The name of the key pair")
@click.option('--instance-type',
              cls=MultiWordOption, type=str,
              help="Instance type")
@click.option('--security-group-ids',
              cls=MultiWordOption, type=str, multiple=True,
              help="Security group ids")
@click.option('--security-group-names', type=str, multiple=True,
              help="Security group names")
@click.option('--userdata-file',
              cls=MultiWordOption, type=str,
              help="File path to userdata (can be specified as a relative "
                   "path to the project path)")
@click.option('--iam-role',
              cls=MultiWordOption, type=str,
              help="Instance IAM role")
@click.option('--imds-version',
              cls=MultiWordOption,
              type=click.Choice(EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS),
              help="IMDS version")
@click.option('--version-description',
              cls=MultiWordOption, type=str,
              help="A description for the version of the launch template")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The ec2 launch template tags')
@click.option('--resource-tags',
              cls=MultiWordOption,
              type=DeepDictParamType(), multiple=True,
              help=f'The resource tags. You can specify tags for the '
                   f'following {EC2_LT_RESOURCE_TAGS}. To tag a resource '
                   f'after it has been created')
@verbose_option
@click.pass_context
@timeit()
def ec2_launch_template(ctx, **kwargs):
    """Generates ec2_launch_template deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]

    if kwargs["resource_tags"]:
        kwargs["resource_tags"] = \
            {k: v for d in kwargs["resource_tags"] for k, v in d.items()}
        valid_keys = set(EC2_LT_RESOURCE_TAGS)
        provided_keys = set(kwargs['resource_tags'].keys())
        # Check if provided keys are all valid
        if not provided_keys <= valid_keys:
            invalid_keys = provided_keys - valid_keys
            raise click.BadParameter(
                f"Invalid resource tag keys provided: '{invalid_keys}'. "
                f"Allowed keys are: '{valid_keys}'"
            )

    generator = EC2LaunchTemplateGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"ec2_launch_template '{kwargs['resource_name']}' was added "
                  f"successfully")
    return OK_RETURN_CODE


@meta.command(name='sqs-queue')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="SQS queue name")
@click.option('--region', type=ValidRegionParamType(),
              help="The region where the queue is deployed. Default value is "
                   "the one from syndicate config")
@click.option('--fifo-queue',
              cls=MultiWordOption, type=bool,
              help="If True, the queue is FIFO. Default value is False")
@click.option('--visibility-timeout',
              cls=MultiWordOption,
              type=click.IntRange(min=0, max=43200),
              help="The visibility timeout for the queue. Default value is 30")
@click.option('--delay-seconds',
              cls=MultiWordOption,
              type=click.IntRange(min=0, max=900),
              help="The length of time in seconds for which the delivery "
                   "of all the messages in the queue is delayed. Default "
                   "value is 0")
@click.option('--maximum-message-size',
              cls=MultiWordOption,
              type=click.IntRange(min=1024, max=262144),
              help="The limit of how many bytes a message can contain before "
                   "Amazon SQS rejects it. Default value is 1024")
@click.option('--message-retention-period',
              cls=MultiWordOption,
              type=click.IntRange(min=60, max=1209600),
              help="The length of time in seconds for which Amazon SQS "
                   "retains a message. Default value is 60")
@click.option('--receive-message-wait-time-seconds',
              cls=MultiWordOption,
              type=click.IntRange(min=0, max=20),
              help="The length of time in seconds for which a 'ReceiveMessage'"
                   " action waits for a message to arrive")
@click.option('--dead-letter-target-arn',
              cls=MultiWordOption, type=str,
              help="Arn of a dead-letter queue Amazon SQS moves messages "
                   "after the value of maxReceiveCount is exceeded")
@click.option('--max-receive-count', type=click.IntRange(min=1, max=1000),
              help="The number of times a message is delivered to the source "
                   "queue before being moved to the dead-letter queue. "
                   "Required if 'dead-letter-target-arn' is specified",
              cls=OptionCombined, required_if='dead-letter-target-arn')
@click.option('--kms-master-key-id', type=str,
              help="The id of an AWS-managed customer master key (CMK) for "
                   "Amazon SQS or a custom CMK")
@click.option('--kms-data-key-reuse-period-seconds',
              cls=MultiWordOption,
              type=click.IntRange(min=60, max=86400),
              help="The length of time in seconds for which Amazon SQS can "
                   "reuse a data key to encrypt or decrypt messages before "
                   "calling AWS KMS again")
@click.option('--content-based-deduplication',
              cls=MultiWordOption, type=bool,
              help="Enables content-based deduplication")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def sqs_queue(ctx, **kwargs):
    """Generates sqs queue deployment deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = SQSQueueGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"SQS queue '{kwargs['resource_name']}' was added "
                  f"successfully")
    return OK_RETURN_CODE


@meta.command(name="sns-application")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
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
    USER_LOG.info(f"SNS application '{kwargs['resource_name']}' was added "
                  f"successfully")
    return OK_RETURN_CODE


@meta.command(name="cognito-user-pool")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Cognito user pool name")
# @click.option('--region', type=ValidRegionParamType(), required=True,
#               help="The region where the user pool is created")
@click.option('--auto-verified-attributes',
              cls=MultiWordOption,
              type=click.Choice(['phone_number', 'email']),
              help="The attributes to be auto-verified. "
                   "Default value is email", multiple=True)
@click.option('--sns-caller-arn',
              cls=MultiWordOption, type=str,
              help="The arn of the IAM role in your account which Cognito "
                   "will use to send SMS messages. Required if 'phone_number' "
                   "in 'auto-verified-attributes' is specified")
@click.option('--username-attributes',
              cls=MultiWordOption,
              type=click.Choice(['phone_number', 'email']),
              help="Specifies whether email addresses or phone numbers can "
                   "be specified as usernames when a user signs up. Default "
                   "value is email", multiple=True)
@click.option('--custom-attributes',
              cls=MultiWordOption, type=(str, str), multiple=True,
              help="A list of custom attributes: (name type)")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def cognito_user_pool(ctx, **kwargs):
    """Generates cognito user pool deployment resource template"""
    if 'phone_number' in kwargs['auto_verified_attributes'] \
            and not kwargs.get('sns_caller_arn'):
        raise click.MissingParameter("Sns caller IAM role arn is required when"
                                     " 'phone_number' is specified in "
                                     "'auto-verified-attributes'",
                                     param_type='option',
                                     param_hint='sns-caller-arn')

    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CognitoUserPoolGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Cognito user pool '{kwargs['resource_name']}' was added "
                  f"successfully")
    return OK_RETURN_CODE


@meta.command(name="cognito-federated-pool")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Cognito federated pool name")
@click.option('--auth-role',
              cls=MultiWordOption, type=str,
              help="IAM role for authorized users")
@click.option('--unauth-role',
              cls=MultiWordOption, type=str,
              help="IAM role for unauthorized users")
@click.option('--open-id-providers',
              cls=MultiWordOption, type=str, multiple=True,
              help="A list of OpenID Connect providers")
@click.option('--provider-name',
              cls=MultiWordOption, type=str,
              help="Developer provider name")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def cognito_federated_pool(ctx, **kwargs):
    """Generates cognito federated pool deployment resource template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CognitoFederatedPoolGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Cognito federated pool '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='batch-compenv')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Batch compute environment name")
@click.option('--compute-environment-type',
              cls=MultiWordOption,
              type=click.Choice(['MANAGED', 'UNMANAGED']),
              help="The type of compute environment. "
                   "Default value is 'MANAGED'")
@click.option('--allocation-strategy',
              cls=MultiWordOption,
              type=click.Choice(['BEST_FIT', 'BEST_FIT_PROGRESSIVE',
                                 'SPOT_CAPACITY_OPTIMIZED']),
              help="The allocation strategy to use for the compute resource "
                   "if not enough instances of the best fitting instance type "
                   "can be allocated")
@click.option('--state', type=click.Choice(['ENABLED', 'DISABLED']),
              help="The state of compute environment")
@click.option('--service-role',
              cls=MultiWordOption, type=str,
              help="The full Amazon Resource Name (ARN) of the IAM role that "
                   "allows Batch to make calls to other Amazon Web Services "
                   "services on your behalf. If not specified, role "
                   "'AWSBatchServiceRole' will be taken if it exists, if "
                   "doesn't it'll be created")
@click.option('--type',
              type=click.Choice(['EC2', 'SPOT', 'FARGATE', 'FARGATE_SPOT']),
              help="The type of compute environment. Default value is EC2")
@click.option('--minv-cpus',
              cls=MultiWordOption, type=click.IntRange(min=0),
              help='The minimum number of Amazon EC2 vCPUs that an '
                   'environment should maintain. Default value is 0')
@click.option('--maxv-cpus',
              cls=MultiWordOption, type=click.IntRange(min=1),
              help="The maximum number of Amazon EC2 vCPUs that a compute "
                   "environment can reach. Default value is 8")
@click.option('--desiredv-cpus',
              cls=MultiWordOption, type=int,
              help="The desired number of Amazon EC2 vCPUS in the compute "
                   "environment. Default value is 1")
@click.option('--instance-types',
              cls=MultiWordOption, type=str, multiple=True,
              help="The instances types that can be launched. Default value "
                   "is 'optimal'")
@click.option('--security-group-ids',
              cls=MultiWordOption, type=str,
              multiple=True, required=True,
              help="The Amazon EC2 security groups associated with instances "
                   "launched in the compute environment")
@click.option('--subnets', type=str, multiple=True, required=True,
              help="The VPC subnets where the compute resources are launched")
@click.option('--instance-role',
              cls=MultiWordOption, type=str,
              help="The Amazon ECS instance profile applied to Amazon EC2 "
                   "instances in a compute environment")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def batch_compenv(ctx, **kwargs):
    """Generates batch compenv deployment resources template"""
    if kwargs.get('type') != 'FARGATE':
        if not kwargs.get('instance_role'):
            raise click.MissingParameter(
                "'instance-role' is required if batch compenv type "
                "ISN'T 'FARGATE'",
                param_type='option',
                param_hint='instance-role')
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchCompenvGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Batch compute environment '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='batch-jobdef')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help='Batch job definition name')
@click.option('--job-definition-type',
              cls=MultiWordOption, required=True,
              type=click.Choice(['container', 'multinode']),
              help='The type of job definition')
@click.option('--image', type=str,
              help='The image used to start a container. '
                   'Default value is \'alpine\'')
@click.option('--job-role-arn',
              cls=MultiWordOption, type=str,
              help='The ARN of the IAM role that the container can assume for '
                   'AWS permissions')
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def batch_jobdef(ctx, **kwargs):
    """Generates batch job definition deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchJobdefGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f'Batch job definition \'{kwargs["resource_name"]}\' was '
                  f'added successfully')
    return OK_RETURN_CODE


@meta.command(name="batch-jobqueue")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Batch job queue name")
@click.option('--state', type=click.Choice(["ENABLED", "DISABLED"]),
              help="The state of the job queue. Default value is 'ENABLED'")
@click.option('--priority', type=int, help="The priority of the job queue. "
                                           "Default value is 1")
@click.option('--compute-environment-order',
              cls=MultiWordOption, type=(int, str), multiple=True,
              help="The set of compute environments mapped to a job queue and "
                   "their order relative to each other. (order, compute_env)")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def batch_jobqueue(ctx, **kwargs):
    """Generates batch job queue deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = BatchJobqueueGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Batch job queue '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="cloudwatch-alarm")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Cloudwatch alarm name")
@click.option('--metric-name',
              cls=MultiWordOption, type=str, required=True,
              help="The metric's name")
@click.option('--namespace', type=str, required=True,
              help="The namespace for the metric associated with the alarm")
@click.option('--description', type=str, help="The description for the alarm")
@click.option('--period', type=click.IntRange(min=1),
              help="The period in seconds over which the specified statistic "
                   "is applied. Valid values are 10, 30 and any multiple"
                   " of 60. Default value is 1200")
@click.option('--evaluation-periods',
              cls=MultiWordOption, type=click.IntRange(min=1),
              help="The number of periods over which data is compared to the "
                   "specified threshold. Default value is 1")
@click.option('--threshold', type=float,
              help="The value to compare with the specified statistic. "
                   "Default value is 1.0")
@click.option('--comparison-operator',
              cls=MultiWordOption,
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
@click.option('--sns-topics',
              cls=MultiWordOption, type=str, multiple=True,
              help="The sns topics to execute when the alarm goes to an ALARM "
                   "state from any other state")
@click.option('--lambdas', type=str, multiple=True,
              help="The lambdas to execute when the alarm goes to an ALARM "
                   "state from any other state. Use `:` after lambda name to "
                   "specify alias or version")
@click.option('--ssm-response-plan',
              cls=MultiWordOption, type=str, multiple=True,
              help="The response plan name to execute when the alarm goes to "
                   "an ALARM state from any other state")
@click.option('--evaluate-low-sample-count-percentile',
              cls=MultiWordOption,
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
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def cloudwatch_alarm(ctx, **kwargs):
    """Generates Cloudwatch alarm deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CloudWatchAlarmGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Cloudwatch alarm '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="cloudwatch-event-rule")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="Cloudwatch event rule name")
@click.option('--rule-type', cls=MultiWordOption,
              required=True, help="Cloudwatch event rule type",
              type=click.Choice(['schedule', 'ec2', 'api_call']))
@click.option('--expression', type=str,
              help="Rule expression (cron schedule). Valuable only if "
                   "rule_type is 'schedule'")
@click.option('--aws-service',
              cls=MultiWordOption, type=str,
              help="The name of AWS service which the rule listens to. "
                   "Required only if rule_type is 'api_call'")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              help="The region where the rule is deployed. Default value is "
                   "the one from syndicate config")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def cloudwatch_event_rule(ctx, **kwargs):
    """Generates Cloudwatch event rule deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = CloudwatchEventRuleGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"Cloudwatch event rule '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="eventbridge-rule")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="EventBridge rule name")
@click.option('--rule-type', cls=MultiWordOption,
              required=True, help="EventBridge rule type",
              type=click.Choice(['schedule', 'ec2', 'api_call']))
@click.option('--expression', type=str,
              help="Rule expression (cron schedule). Valuable only if "
                   "rule-type is 'schedule'")
@click.option('--aws-service',
              cls=MultiWordOption, type=str,
              help="The name of AWS service which the rule listens to. "
                   "Required only if rule-type is 'api_call'")
@click.option('--region', type=ValidRegionParamType(allowed_all=True),
              help="The region where the rule is deployed. Default value is "
                   "the one from syndicate config")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def eventbridge_rule(ctx, **kwargs):
    """Generates EventBridge rule deployment resources-template
    claiming compatibility with Cloudwatch event rule generator"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = EventBridgeRuleGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"EventBridge rule '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="documentdb-cluster")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="DocumentDB cluster name")
@click.option('--master-username',
              cls=MultiWordOption, type=str, required=True,
              help="DocumentDB login ID for the master user")
@click.option('--master-password',
              cls=MultiWordOption, type=str, required=True,
              help="The password for master user")
@click.option('--port', type=int,
              help="The port number on which the instances in the cluster "
                   "accept connections. Default value is 27017")
@click.option('--vpc-security-group-ids',
              cls=MultiWordOption, type=str, multiple=True,
              help="A list of EC2 VPC security groups to associate with this "
                   "cluster. If not specified, default security group is used")
@click.option('--availability-zones',
              cls=MultiWordOption, type=str, multiple=True,
              help="A list of Amazon EC2 Availability Zones that instances in "
                   "the cluster can be created in. "
                   "If not specified default is used")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def documentdb_cluster(ctx, **kwargs):
    """Generates documentdb cluster deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DocumentDBClusterGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"DocumentDB cluster '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="documentdb-instance")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="DocumentDB instance name")
@click.option('--cluster-identifier',
              cls=MultiWordOption, type=str, required=True,
              help="The identifier of the cluster that the instance will "
                   "belong to")
@click.option('--instance-class',
              cls=MultiWordOption, type=str,
              help="The compute and memory capacity of the instance. Default "
                   "value is 'db.r5.large'")
@click.option('--availability-zone',
              cls=MultiWordOption, type=str,
              help="The Amazon EC2 Availability Zone that the instance is "
                   "created in. If not specified a random zone it the "
                   "endpoint's region is set")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def documentdb_instance(ctx, **kwargs):
    """Generates documentdb instance deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = DocumentDBInstanceGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"DocumentDB instance '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name='firehose')
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help='Kinesis Data Firehose delivery stream name')
@click.option('--stream-type',
              cls=MultiWordOption,
              type=click.Choice(['DirectPut', 'KinesisStreamAsSource']),
              default='DirectPut', is_eager=True,
              help='The delivery stream type.')
@click.option('--kinesis-stream-arn',
              type=str, cls=OptionCombined,
              required_if='stream-type',
              required_if_values=['KinesisStreamAsSource'],
              help='The ARN of the source Kinesis data stream. [Required if '
                   'stream-type is \'KinesisStreamAsSource\']')
@click.option('--kinesis-stream-role',
              type=str, cls=OptionCombined,
              required_if='stream-type',
              required_if_values=['KinesisStreamAsSource'],
              help='The role name that provides access to the Kinesis data '
                   'stream source. [Required if stream-type is '
                   '\'KinesisStreamAsSource\']')
@click.option('--destination-role',
              cls=MultiWordOption, type=str, required=True,
              help='The role name that provides access to the Kinesis data '
                   'stream destination S3 bucket.')
@click.option('--destination-bucket',
              cls=MultiWordOption, type=str, required=True,
              help='The Kinesis data stream destination S3 bucket name.')
@click.option('--compression-format',
              cls=MultiWordOption, type=click.Choice(
             ['UNCOMPRESSED', 'GZIP', 'ZIP', 'Snappy', 'HADOOP_SNAPPY']),
              default='UNCOMPRESSED',
              help='The compression format.')
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def firehose(ctx, **kwargs):
    """Generates Kinesis Data Firehose delivery stream deployment resources
    template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = FirehoseGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"The Kinesis Data Firehose delivery stream "
                  f"'{kwargs['resource_name']}' was added successfully")
    return OK_RETURN_CODE


@meta.command(name="eventbridge-schedule")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="EventBridge scheduler name")
@click.option('--schedule-expression',
              cls=MultiWordOption, type=str, required=True,
              help="The expression that defines when the schedule runs. "
                   "The following formats are supported: "
                   "at(yyyy-mm-ddThh:mm:ss); rate(value unit); cron(fields)")
@click.option('--target-arn',
              cls=MultiWordOption, type=str, required=True,
              help="The complete service ARN, including the API operation, in "
                   "the following format: "
                   "`arn:aws:scheduler:::aws-sdk:service:apiAction`. "
                   "For example: arn:aws:scheduler:::aws-sdk:sqs:sendMessage")
@click.option('--role-arn',
              cls=MultiWordOption, type=str, required=True,
              help="The execution role ARN you want to use for the target. "
                   "This role must have the permissions to call the "
                   "API operation you want your schedule to target")
@click.option('--mode', type=click.Choice(['OFF', 'FLEXIBLE']), default='OFF',
              help="Determines whether the schedule is invoked within a "
                   "flexible time window")
@click.option('--maximum-window-in-minutes',
              type=click.IntRange(min=5),
              cls=OptionCombined, required_if='mode',
              required_if_values=['FLEXIBLE'],
              help="The maximum time window during which a schedule can be "
                   "invoked")
@click.option('--description', type=str, help="Schedule description")
@click.option('--schedule-expression-timezone',
              cls=MultiWordOption, type=str,
              help="The timezone in which the scheduling expression "
                   "is evaluated.")
@click.option('--group-name',
              cls=MultiWordOption, type=str,
              help="The name of the schedule group to associate with this "
                   "schedule. By default, the default schedule group is used.")
@click.option('--kms-key-arn',
              cls=MultiWordOption, type=str,
              help="ARN for the customer managed KMS key that scheduler "
                   "will use to encrypt and decrypt data")
@click.option('--state', type=click.Choice(['ENABLED', 'DISABLED']),
              help="Specifies whether the schedule is enabled or disabled")
@click.option('--start-date',
              cls=MultiWordOption, type=str,
              help=" A date in ISO 8601 or UTC, after which the schedule "
                   "can begin invoking its target")
@click.option('--end-date',
              cls=MultiWordOption, type=str,
              help="A date in ISO 8601 or UTC, before which the schedule "
                   "can invoke its target")
@click.option('--dead-letter-arn',
              cls=MultiWordOption, type=str,
              help="SQS queue ARN that will be as the destination "
                   "for the dead-letter queue.")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def eventbridge_schedule(ctx, **kwargs):
    """Generates eventbridge scheduler deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    generator = EventBridgeScheduleGenerator(**filtered_kwargs)
    _generate(generator)
    USER_LOG.info(f"EventBridge scheduler '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="rds-db-cluster")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="DB cluster name")
@click.option('--engine', default='aurora-postgresql',
              type=click.Choice(['aurora-postgresql', 'aurora-mysql']),
              help="Engine type. Default type: aurora-postgresql")
@click.option('--engine-version',
              cls=MultiWordOption, type=str,
              help="Engine version")
@click.option('--master-username',
              cls=MultiWordOption, type=str, required=True,
              help="DB login ID for the master user")
@click.option('--master-password',
              cls=MultiWordOption, type=str,
              callback=partial(
                  validate_incompatible_options,
                  incompatible_options=['manage-master-password']),
              help="The password for master user. Can't be specified if "
                   "manage-master-password is turned on")
@click.option('--database-name',
              cls=MultiWordOption, type=str, required=True,
              help="Database name")
@click.option('--port', type=int,
              help="The port number on which the instances in the cluster "
                   "accept connections. Default value is 3306 for MySQL and "
                   "5432 for PostgreSQL")
@click.option('--manage-master-password',
              cls=MultiWordOption, type=bool, is_eager=True,
              help="Indicates whether to manage the master user password with "
                   "AWS Secrets Manager")
@click.option('--iam-db-auth',
              cls=MultiWordOption, type=bool,
              help="Indicates whether to enable IAM Database Authentication")
@click.option('--vpc-security-group-ids',
              cls=MultiWordOption, type=str, multiple=True,
              help="A list of EC2 VPC security groups to associate with this "
                   "cluster. If not specified, default security group is used")
@click.option('--db-subnet-group',
              cls=MultiWordOption, type=str,
              help="RDS subnet group name to associate with the DB cluster")
@click.option('--availability-zones',
              cls=MultiWordOption, type=str, multiple=True,
              help="A list of Amazon EC2 Availability Zones that instances in "
                   "the cluster can be created in. "
                   "If not specified default is used")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def rds_db_cluster(ctx, **kwargs):
    """Generates RDS DB cluster deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = RDSDBClusterGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"RDS DB cluster '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


@meta.command(name="rds-db-instance")
@return_code_manager
@click.option('--resource-name',
              cls=MultiWordOption, type=str, required=True,
              help="DB instance name")
@click.option('--instance-class',
              cls=MultiWordOption, type=str, required=True,
              help="DB instance class")
@click.option('--cluster-name',
              cls=MultiWordOption, type=str,
              callback=partial(
                  validate_incompatible_options,
                  incompatible_options=
                  RDS_INSTANCE_DB_CLUSTER_INCOMPATIBLE_OPTIONS),
              help="RDS DB cluster name to link the instance with")
@click.option('--engine', type=str, is_eager=True,
              help="Engine type")
@click.option('--engine-version',
              cls=MultiWordOption, type=str, is_eager=True,
              help="Engine version")
@click.option('--master-username',
              cls=MultiWordOption, type=str, is_eager=True,
              help="DB login ID for the master user")
@click.option('--master-password',
              cls=MultiWordOption, type=str, is_eager=True,
              help="The password for master user")
@click.option('--database-name',
              cls=MultiWordOption, type=str, is_eager=True,
              help="Database name")
@click.option('--port', type=int, is_eager=True,
              help="The port number on which the instances in the cluster "
                   "accept connections")
@click.option('--publicly-accessible',
              cls=MultiWordOption, type=bool,
              help="Specifies the accessibility options for the DB instance.")
@click.option('--vpc-security-group-ids',
              cls=MultiWordOption, type=str, multiple=True,
              is_eager=True,
              help="A list of EC2 VPC security groups to associate with this "
                   "cluster. If not specified, default security group is used")
@click.option('--availability-zone',
              cls=MultiWordOption, type=str, is_eager=True,
              help="Amazon EC2 Availability Zone that instances can be "
                   "created in. If not specified default is used")
@click.option('--tags', type=DictParamType(), callback=check_tags,
              help='The resource tags')
@verbose_option
@click.pass_context
@timeit()
def rds_db_instance(ctx, **kwargs):
    """Generates RDS DB instance deployment resources template"""
    kwargs[PROJECT_PATH_PARAM] = ctx.obj[PROJECT_PATH_PARAM]
    generator = RDSDBInstanceGenerator(**kwargs)
    _generate(generator)
    USER_LOG.info(f"RDS DB cluster '{kwargs['resource_name']}' was "
                  f"added successfully")
    return OK_RETURN_CODE


def _generate(generator: BaseConfigurationGenerator):
    """Just some common actions for this module are gathered in here"""
    try:
        generator.write()
    except AbortedError as e:
        raise click.Abort(e)
    except Exception as e:
        if isinstance(e, SyndicateBaseError):
            raise click.BadParameter(e)
        raise Exception(f"An unexpected error occurred: {e}")

