"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
from time import time
from uuid import uuid1

from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.core import CONFIG, CONN
from syndicate.core.build.meta_processor import S3_PATH_NAME
from syndicate.core.helper import create_pool, unpack_kwargs
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.ebs_resource')

_EC2_CONN = CONN.ec2()
_IAM_CONN = CONN.iam()
_EBS_CONN = CONN.beanstalk()


def _describe_ebs(name, meta, response):
    arn = 'arn:aws:elasticbeanstalk:{0}:{1}:application/{2}'.format(
        CONFIG.region, CONFIG.account_id, name)
    return {
        arn: build_description_obj(response, name, meta)
    }


def create_ebs(args):
    return create_pool(_create_ebs_app_env_from_meta, args, 5)


@unpack_kwargs
def _create_ebs_app_env_from_meta(name, meta):
    response = _EBS_CONN.describe_applications([name])
    if response:
        _LOG.warn('%s EBS app exists.', name)
        return _describe_ebs(name, meta, response[0])

    env_settings = meta['env_settings']
    topic_name = meta.get('notification_topic')
    # check topic exists
    if topic_name:
        topic_arn = CONN.sns().get_topic_arn(topic_name)
        if topic_arn:
            env_settings.append({
                "OptionName": "Notification Topic ARN",
                "Namespace": "aws:elasticbeanstalk:sns:topics",
                "Value": "{0}".format(topic_arn)
            })
        else:
            raise AssertionError('Cant find notification '
                                 'topic {0} for EBS.'.format(topic_name))
    # check key pair exists
    key_pair_name = meta['ec2_key_pair']
    if _EC2_CONN.if_key_pair_exists(key_pair_name):
        env_settings.append({
            "OptionName": "KeyName",
            "ResourceName": "AWSEBAutoScalingLaunchConfiguration",
            "Namespace": "aws:cloudformation:template:resource:property",
            "Value": key_pair_name
        })
    else:
        raise AssertionError('Specified key pair '
                             'does not exist: {0}.'.format(key_pair_name))
    # check ec2 role exists
    iam_role = meta['ec2_role']
    if _IAM_CONN.check_if_role_exists(iam_role):
        env_settings.append({
            "OptionName": "IamInstanceProfile",
            "ResourceName": "AWSEBAutoScalingLaunchConfiguration",
            "Namespace": "aws:autoscaling:launchconfiguration",
            "Value": iam_role
        })
    else:
        raise AssertionError(
            'Specified iam role does not exist: {0}.'.format(iam_role))
    # check service role exists
    iam_role = meta['ebs_service_role']
    if _IAM_CONN.check_if_role_exists(iam_role):
        env_settings.append({
            "OptionName": "ServiceRole",
            "Namespace": "aws:elasticbeanstalk:environment",
            "Value": iam_role
        })
    else:
        raise AssertionError('Specified iam role '
                             'does not exist: {0}.'.format(iam_role))
    image_id = meta.get('image_id')
    if image_id:
        env_settings.append({
            "OptionName": "ImageId",
            "ResourceName": "AWSEBAutoScalingLaunchConfiguration",
            "Namespace": "aws:autoscaling:launchconfiguration",
            "Value": image_id
        })
    else:
        _LOG.warn('Image id is not specified.')
    # check that desired solution stack exists
    stack = meta['stack']
    available_stacks = _EBS_CONN.describe_available_solutions_stack_names()
    if stack not in available_stacks:
        raise AssertionError('No solution stack named {0} found.'
                             ' Available:\n{1}'.format(stack,
                                                       available_stacks))
    vpc_id = next(
        (option for option in env_settings if option['OptionName'] == 'VPCId'),
        None)
    if not vpc_id:
        vpc_id = _EC2_CONN.get_default_vpc_id()
        _LOG.info('Default vpc id %s', vpc_id)
        if vpc_id:
            _LOG.debug('Will use vpc %s', vpc_id)
            subnets = _EC2_CONN.list_subnets(filters=[{
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }])
            _LOG.debug('Found subnets for %s vpc: %s', vpc_id, subnets)
            if subnets:
                _LOG.info('Will attach default %s vpc to env', vpc_id)
                _add_subnets_info(env_settings, subnets, vpc_id)
            sg_id = _EC2_CONN.get_sg_id(group_name='default', vpc_id=vpc_id)
            if sg_id:
                _LOG.debug('Found default sg with id %s', sg_id)
                env_settings.append({
                    "OptionName": "SecurityGroups",
                    "Namespace": "aws:autoscaling:launchconfiguration",
                    "Value": sg_id
                })

    env_name = meta["env_name"] + str(int(time()))

    start = time()
    end = start + 180
    while end > time():
        describe_app_result = _EBS_CONN.describe_applications([name])
        if not describe_app_result:
            break

    # create APP
    response = _EBS_CONN.create_application(name)
    _LOG.info('Created EBS app %s.', name)
    # create ENV
    _EBS_CONN.create_environment(app_name=name,
                                 env_name=env_name,
                                 option_settings=env_settings,
                                 tier=meta['tier'],
                                 solution_stack_name=stack)
    key = meta[S3_PATH_NAME]
    if not CONN.s3().is_file_exists(CONFIG.deploy_target_bucket, key):
        raise AssertionError('Deployment package does not exist in '
                             '{0} bucket'.format(CONFIG.deploy_target_bucket))

    # create VERSION
    version_label = env_name + str(uuid1())
    _EBS_CONN.create_app_version(app_name=name, version_label=version_label,
                                 s3_bucket=CONFIG.deploy_target_bucket,
                                 s3_key=key)
    _LOG.debug('Waiting for beanstalk env %s', env_name)
    # wait for env creation
    start = time()
    status = {}
    end = start + 360  # end in 6 min
    while end > time():
        status = _EBS_CONN.describe_environment_health(env_name=env_name,
                                                       attr_names=['Status'])
        if status['Status'] == 'Ready':
            _LOG.info('Launching env took %s.', time() - start)
            break
    if status['Status'] != 'Ready':
        _LOG.error('Env status: %s. Failed to create env.', status)
    # deploy new app version
    _EBS_CONN.deploy_env_version(name, env_name, version_label)
    _LOG.info('Created environment for %s.', name)
    return _describe_ebs(name, meta, response)


def _add_subnets_info(env_settings, subnets, vpc_id):
    env_settings.append({
        "OptionName": "VPCId",
        "Namespace": "aws:ec2:vpc",
        "Value": vpc_id
    })
    subnets = ",".join(subnet['SubnetId'] for subnet in subnets)
    env_settings.append({
        "OptionName": "Subnets",
        "Namespace": "aws:ec2:vpc",
        "Value": subnets
    })


def remove_ebs_apps(args):
    create_pool(_remove_ebs_app, args, 5)


@unpack_kwargs
def _remove_ebs_app(arn, config):
    app_name = config['resource_name']
    try:
        _EBS_CONN.remove_app(app_name)
        _LOG.info('EBS app %s was removed.', app_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            _LOG.warn('EBS app %s is not found', app_name)
        else:
            raise e
