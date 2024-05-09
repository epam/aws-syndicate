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
import base64
import os
from time import sleep

from syndicate.commons.log_helper import get_logger
from syndicate.connection.ec2_connection import InstanceTypes
from syndicate.core import ClientError
from syndicate.core.helper import unpack_kwargs, \
    dict_keys_to_capitalized_camel_case
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

    def describe_launch_template(self, name, meta, response=None):
        if not response:
            response = self.ec2_conn.describe_launch_templates(lt_name=name)
        else:
            response = [response['LaunchTemplate']]
        lt_id = response[0]['LaunchTemplateId']
        return {
            lt_id: build_description_obj(response, name, meta)
        }

    def create_launch_template(self, args):
        return self.create_pool(self._create_launch_template_from_meta, args)

    @unpack_kwargs
    def _create_launch_template_from_meta(self, name, meta):
        lt_data = self._prepare_launch_template_data(meta)
        response = self.ec2_conn.create_launch_template(
            name=name,
            lt_data=dict_keys_to_capitalized_camel_case(lt_data),
            version_description=meta.get('version_description'),
            tag_specifications=dict_keys_to_capitalized_camel_case(
                meta['tag_specifications']) if
            meta.get('tag_specifications') else None
        )
        return self.describe_launch_template(name, meta, response)

    def remove_launch_templates(self, args):
        return self.create_pool(self._remove_launch_template, args)

    @unpack_kwargs
    def _remove_launch_template(self, arn, config):
        try:
            self.ec2_conn.delete_launch_template(lt_id=arn)
            _LOG.info(f"Launch template with ID '{arn}' removed "
                      f"successfully")
        except ClientError as e:
            if 'InvalidLaunchTemplateId.NotFound' in str(e):
                _LOG.warn(f"Launch template with ID '{arn}' not found")
            else:
                raise e

    def update_launch_template(self, args):
        return self.create_pool(self._update_launch_template_from_meta, args)

    @unpack_kwargs
    def _update_launch_template_from_meta(self, name, meta, context):
        lt_data = self._prepare_launch_template_data(meta)
        lt_description = self.ec2_conn.describe_launch_templates(lt_name=name)
        if not lt_description:
            raise AssertionError(
                f"Launch template with name '{name}' not found")
        lt_latest_version = lt_description[0]['LatestVersionNumber']
        self.ec2_conn.create_launch_template_version(
            lt_name=name,
            source_version=str(lt_latest_version),
            lt_data=dict_keys_to_capitalized_camel_case(lt_data),
            version_description=meta.get('version_description')
        )
        response = self.ec2_conn.modify_launch_template(
            lt_name=name,
            default_version=str(lt_latest_version + 1))
        return self.describe_launch_template(name, meta, response)

    def _prepare_launch_template_data(self, meta):
        from syndicate.core import CONFIG
        lt_data = meta['launch_template_data']
        lt_imds = lt_data.pop('imds_support', None)
        image_id = lt_data.get('image_id')
        if image_id:
            image_data = self.ec2_conn.describe_image(image_id=image_id)
            if not image_data:
                raise AssertionError(f'Image id {image_id} is invalid')

        if lt_imds:
            metadata_options = {'http_tokens': 'required'} \
                if lt_imds == 'v2.0' else {'http_tokens': 'optional'}
            lt_data['metadata_options'] = metadata_options

        key_name = lt_data.get('key_name')
        if key_name and not self.ec2_conn.if_key_pair_exists(key_name):
            raise AssertionError(f'There is no key pair with name: {key_name}')

        security_groups_names = lt_data.get('security_groups')
        if security_groups_names:
            sg_meta = self.ec2_conn.describe_security_groups(
                security_groups_names)
            described_sec_groups_names = [security_group['GroupName']
                                          for security_group in sg_meta]
            for security_group_name in security_groups_names:
                if security_group_name not in described_sec_groups_names:
                    raise AssertionError(
                        f'Security group {security_group_name} does not exist')

        security_group_ids = lt_data.get('security_group_ids')
        if security_group_ids:
            sg_meta = self.ec2_conn.describe_security_groups(
                sg_id=security_group_ids)
            described_sec_group_ids = [security_group['GroupId']
                                       for security_group in sg_meta]
            for security_group_id in security_group_ids:
                if security_group_id not in described_sec_group_ids:
                    raise AssertionError(f'Security group with ID '
                                         f'{security_group_id} does not exist')

        iam_role_name = lt_data.pop('iam_role', None)
        if iam_role_name:
            instance_profiles = self.iam_conn.get_instance_profiles_for_role(
                role_name=iam_role_name)
            if instance_profiles:
                iam_profile_meta = instance_profiles[0]
                lt_data['iam_instance_profile'] = {
                    'arn': iam_profile_meta['Arn'],
                    'name': iam_profile_meta['InstanceProfileName']
                }

        user_data_file_path = lt_data.pop('userdata_file', None)
        if user_data_file_path:
            user_data_content = None
            if not os.path.isabs(user_data_file_path):
                user_data_file_path = os.path.join(CONFIG.project_path,
                                                   user_data_file_path)
            if not os.path.isfile(user_data_file_path):
                _LOG.warn(f'There is no user data found by path '
                          f'{user_data_file_path}. ')
            else:
                with open(user_data_file_path, 'r') as userdata_file:
                    user_data_content = userdata_file.read()
            if user_data_content:
                user_data_b = \
                    base64.b64encode(user_data_content.encode("ascii"))
                user_data = user_data_b.decode('ascii')
                lt_data['user_data'] = user_data

        return lt_data
