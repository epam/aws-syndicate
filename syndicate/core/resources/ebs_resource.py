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
from syndicate.core.build.meta_processor import S3_PATH_NAME
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj

_LOG = get_logger('syndicate.core.resources.ebs_resource')


class EbsResource(BaseResource):

    def __init__(self, ec2_conn, iam_conn, ebs_conn, sns_conn,
                 s3_conn, region, account_id, deploy_target_bucket) -> None:
        self.ec2_conn = ec2_conn
        self.iam_conn = iam_conn
        self.ebs_conn = ebs_conn
        self.sns_conn = sns_conn
        self.s3_conn = s3_conn
        self.region = region
        self.account_id = account_id
        self.deploy_target_bucket = deploy_target_bucket

    def describe_ebs(self, name, meta, response=None):
        arn = f'arn:aws:elasticbeanstalk:{self.region}:{self.account_id}' \
            f':application/{name}'
        if not response:
            response = self.ebs_conn.describe_applications([name])
        return {
            arn: build_description_obj(response, name, meta)
        }

    def create_ebs(self, args):
        return self.create_pool(self._create_ebs_app_env_from_meta, args)

    @unpack_kwargs
    def _create_ebs_app_env_from_meta(self, name, meta):
        response = self.ebs_conn.describe_applications([name])
        if response:
            _LOG.warn(f'{name} EBS app exists.')
            return self.describe_ebs(name, meta, response[0])

        env_settings = meta['env_settings']
        topic_name = meta.get('notification_topic')
        # check topic exists
        if topic_name:
            topic_arn = self.sns_conn.get_topic_arn(topic_name)
            if topic_arn:
                env_settings.append({
                    "OptionName": "Notification Topic ARN",
                    "Namespace": "aws:elasticbeanstalk:sns:topics",
                    "Value": topic_arn
                })
            else:
                raise AssertionError('Cant find notification '
                                     'topic {0} for EBS.'.format(topic_name))
        # check key pair exists
        key_pair_name = meta['ec2_key_pair']
        if self.ec2_conn.if_key_pair_exists(key_pair_name):
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
        if self.iam_conn.check_if_role_exists(iam_role):
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
        if self.iam_conn.check_if_role_exists(iam_role):
            env_settings.append({
                "OptionName": "ServiceRole",
                "Namespace": "aws:elasticbeanstalk:environment",
                "Value": iam_role
            })
        else:
            raise AssertionError(f'Specified iam role '
                                 f'does not exist: {iam_role}.')
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
        available_stacks = self.ebs_conn. \
            describe_available_solutions_stack_names()
        if stack not in available_stacks:
            raise AssertionError(f'No solution stack named {stack} found.'
                                 f' Available:\n{available_stacks}')
        vpc_id = next(
            (option for option in env_settings if
             option['OptionName'] == 'VPCId'),
            None)
        if not vpc_id:
            vpc_id = self.ec2_conn.get_default_vpc_id()
            _LOG.info('Default vpc id %s', vpc_id)
            if vpc_id:
                _LOG.debug('Will use vpc %s', vpc_id)
                subnets = self.ec2_conn.list_subnets(filters=[{
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                }])
                _LOG.debug(f'Found subnets for {vpc_id} vpc: {subnets}')
                if subnets:
                    _LOG.info(f'Will attach default {vpc_id} vpc to env')
                    self._add_subnets_info(env_settings, subnets, vpc_id)
                sg_id = self.ec2_conn.get_sg_id(group_name='default',
                                                vpc_id=vpc_id)
                if sg_id:
                    _LOG.debug(f'Found default sg with id {sg_id}')
                    env_settings.append({
                        "OptionName": "SecurityGroups",
                        "Namespace": "aws:autoscaling:launchconfiguration",
                        "Value": sg_id
                    })

        env_name = meta["env_name"] + str(int(time()))

        start = time()
        end = start + 180
        while end > time():
            describe_app_result = self.ebs_conn.describe_applications([name])
            if not describe_app_result:
                break

        # create APP
        response = self.ebs_conn.create_application(name)
        _LOG.info(f'Created EBS app {name}.')
        # create ENV
        self.ebs_conn.create_environment(app_name=name,
                                         env_name=env_name,
                                         option_settings=env_settings,
                                         tier=meta['tier'],
                                         solution_stack_name=stack)
        key = meta[S3_PATH_NAME]
        if not self.s3_conn.is_file_exists(self.deploy_target_bucket, key):
            raise AssertionError(f'Deployment package does not exist in '
                                 f'{self.deploy_target_bucket} bucket')

        # create VERSION
        version_label = env_name + str(uuid1())
        self.ebs_conn.create_app_version(app_name=name,
                                         version_label=version_label,
                                         s3_bucket=self.deploy_target_bucket,
                                         s3_key=key)
        _LOG.debug(f'Waiting for beanstalk env {env_name}')
        # wait for env creation
        start = time()
        status = {}
        end = start + 360  # end in 6 min
        while end > time():
            status = self.ebs_conn.describe_environment_health(
                env_name=env_name,
                attr_names=[
                    'Status'])
            if status['Status'] == 'Ready':
                _LOG.info('Launching env took %s.', time() - start)
                break
        if status['Status'] != 'Ready':
            _LOG.error(f'Env status: {status}. Failed to create env.')
        # deploy new app version
        self.ebs_conn.deploy_env_version(name, env_name, version_label)
        _LOG.info('Created environment for %s.', name)
        return self.describe_ebs(name, meta, response)

    @staticmethod
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

    def remove_ebs_apps(self, args):
        self.create_pool(self._remove_ebs_app, args)

    @unpack_kwargs
    def _remove_ebs_app(self, arn, config):
        app_name = config['resource_name']
        try:
            self.ebs_conn.remove_app(app_name)
            _LOG.info(f'EBS app {app_name} was removed.')
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                _LOG.warn(f'EBS app {app_name} is not found')
            else:
                raise e
