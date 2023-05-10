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
import os
from time import sleep

from syndicate.commons.log_helper import get_logger
from syndicate.connection.ec2_connection import InstanceTypes
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import build_description_obj, chunks

_LOG = get_logger('syndicate.core.resources.ec2_resource')


class Ec2Resource(BaseResource):

    def __init__(self, ec2_conn, iam_conn, region, account_id) -> None:
        self.ec2_conn = ec2_conn
        self.iam_conn = iam_conn
        self.region = region
        self.account_id = account_id

    def describe_ec2(self, name, meta, response=None):
        if not response:
            response = self.ec2_conn.describe_instances()
        arn = 'arn:aws:ec2:{0}:{1}:instance/{2}'.format(self.region,
                                                        self.account_id,
                                                        response['InstanceId'])
        describe_response = self.ec2_conn.describe_instances(
            [
                {
                    'Name': 'instance-id',
                    'Values': [response['InstanceId']]
                }
            ]
        )
        response['NetworkInterfaces'] = describe_response
        return {
            arn: build_description_obj(response, name, meta)
        }

    def create_ec2(self, args):
        return self.create_pool(self._create_ec2_from_meta, args)

    @unpack_kwargs
    def _create_ec2_from_meta(self, name, meta):
        from syndicate.core import CONF_PATH
        # checking required parameters
        image_id = meta['image_id']
        image_data = self.ec2_conn.describe_image(image_id=image_id)
        if not image_data:
            raise AssertionError('Image id {0} is invalid'.format(image_id))

        instance_type = meta.get('instance_type')
        if not instance_type:
            raise AssertionError('Instance type must be specified')
        if instance_type not in InstanceTypes.from_botocore():
            raise AssertionError(f'Not available instance type: {instance_type}')

        key_name = meta.get('key_name')
        if not self.ec2_conn.if_key_pair_exists(key_name):
            raise AssertionError('There is no key pair with name: {0}'
                                 .format(key_name))

        availability_zone = meta.get('availability_zone')
        subnet = meta.get('subnet_id')
        if availability_zone:
            subnet_filter = {
                'Name': 'availabilityZone',
                'Values': [availability_zone]
            }
            subnet_list = self.ec2_conn.list_subnets(filters=[subnet_filter])
            if subnet and subnet not in \
                    [subnet_ids['SubnetId'] for subnet_ids in subnet_list]:
                raise AssertionError(
                    'There is no available Subnets with name {0} '
                    'in Availability Zone {1}.'
                        .format(subnet, availability_zone))
            if availability_zone not in self.ec2_conn.get_azs():
                raise AssertionError(
                    'There is no Availability Zone with name: {0}'
                        .format(availability_zone))

        security_groups_names = meta.get('security_group_names')
        if security_groups_names:
            sg_meta = self.ec2_conn.describe_security_groups(
                security_groups_names)
            described_sec_groups_names = [security_group['GroupName']
                                          for security_group in sg_meta]
            for security_group_name in security_groups_names:
                if security_group_name not in described_sec_groups_names:
                    raise AssertionError('Security group {0} does not exist'
                                         .format(security_group_name))

        # checking optional parameters
        user_data_file_name = meta.get('userdata_file')
        user_data_content = None
        if user_data_file_name:
            user_data_location = os.path.join(CONF_PATH, user_data_file_name)
            if not os.path.isfile(user_data_location):
                _LOG.warn('There is no user data {0} found by path {1}. '
                          .format(user_data_file_name, CONF_PATH))
            else:
                with open(user_data_location, 'r') as userdata_file:
                    user_data_content = userdata_file.read()

        # describing instance profile by iam role name
        iam_role_name = meta.get('iam_role')
        iam_instance_profile_object = None
        if iam_role_name:
            instance_profiles = self.iam_conn.get_instance_profiles_for_role(
                role_name=iam_role_name)
            if instance_profiles:
                iam_profile_meta = instance_profiles[0]
                iam_instance_profile_arn = iam_profile_meta['Arn']
                iam_instance_profile_object = {
                    'Arn': iam_instance_profile_arn
                }

        # launching instance
        response = self.ec2_conn.launch_instance(
            name=name,
            image_id=image_id,
            instance_type=instance_type,
            key_name=key_name,
            tags_list=meta.get('tags_list'),
            security_groups_names=meta.get('security_group_names'),
            security_group_ids=meta.get('security_group_ids'),
            user_data=user_data_content,
            iam_instance_profile=iam_instance_profile_object,
            subnet_id=meta.get('subnet_id'),
            availability_zone=availability_zone
        )

        if meta.get('disableApiTermination'):
            disable_api_termination = meta.get('disableApiTermination')
            _LOG.debug('Found disableApiTermination '
                       'property: {0}'.format(disable_api_termination))
            if str(disable_api_termination).lower() == 'true':
                self.ec2_conn.modify_instance_attribute(
                    InstanceId=response['InstanceId'],
                    DisableApiTermination={
                        'Value': True
                    }
                )
        _LOG.info('Created EC2 instance %s. '
                  'Waiting for instance network interfaces configuring.', name)
        sleep(30)  # time for vm to become running
        return self.describe_ec2(name, meta, response)

    def remove_ec2_instances(self, args):
        for param_chunk in chunks(args, 1000):
            self.remove_instance_list(param_chunk)

    def remove_instance_list(self, instance_list):
        instance_ids = [x['config']['description']['InstanceId'] for x in
                        instance_list]
        existing_instances_list = []
        for instance_id in instance_ids:
            try:
                self.ec2_conn.modify_instance_attribute(
                    InstanceId=instance_id,
                    DisableApiTermination={'Value': False}
                )
                existing_instances_list.append(instance_id)
            except ClientError as e:
                if 'InvalidInstanceID.NotFound' in str(e):
                    _LOG.warn('Instance %s does not exist', instance_id)
                else:
                    raise e

        if existing_instances_list:
            self.ec2_conn.terminate_instances(
                instance_ids=existing_instances_list)
        _LOG.info('EC2 instances %s were removed.',
                  str(existing_instances_list))
