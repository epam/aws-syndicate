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
import inspect
import json
import time
from pathlib import Path
from typing import Generator, Optional, List, Iterable, Any

import botocore
from botocore.exceptions import ClientError
from boto3 import client

from syndicate.exceptions import InvalidValueError, ParameterError
from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry
from syndicate.core.constants import EC2_LT_RESOURCE_TAGS

_LOG = get_logger(__name__)


def create_permissions(ranges):
    ip_ranges = [{'CidrIp': ip_range} for ip_range in ranges]
    return [{
        'IpProtocol': '-1',
        'FromPort': -1,
        'ToPort': -1,
        'IpRanges': ip_ranges
    }]


def preserve_default_permission(group_id, permissions):
    for permission in permissions:
        if 'UserIdGroupPairs' in permission and permission['UserIdGroupPairs']:
            for pair in permission['UserIdGroupPairs']:
                if pair['GroupId'] == group_id:
                    permission.pop('UserIdGroupPairs')


@apply_methods_decorator(retry())
class EC2Connection(object):
    """ EC2 connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('ec2', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new EC2 connection.')

    def describe_security_groups(self, name=None, sg_id=None, vpc_id=None):
        filters = []
        if name:
            if isinstance(name, list):
                filters.append({'Name': 'group-name', 'Values': name})
            elif isinstance(name, str):
                filters.append({'Name': 'group-name', 'Values': [name]})
            else:
                _LOG.warning('Unacceptable name type: %s', type(name))
        if sg_id:
            if isinstance(sg_id, list):
                filters.append({'Name': 'group-id', 'Values': sg_id})
            elif isinstance(sg_id, str):
                filters.append({'Name': 'group-id', 'Values': [sg_id]})
            else:
                _LOG.warning(
                    f'Unacceptable security group id type: {type(sg_id)}')
        if vpc_id:
            filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})
        return self.client.describe_security_groups(Filters=filters)[
            'SecurityGroups']

    def describe_regions(self, name=None):
        filters = []
        if name:
            if isinstance(name, list):
                filters.append({'Name': 'region-name', 'Values': name})
            elif isinstance(name, str):
                filters.append({'Name': 'region-name', 'Values': [name]})
            else:
                _LOG.warning('Unacceptable name type: %s', type(name))
        return self.client.describe_regions(Filters=filters)['Regions']

    def get_default_vpc_id(self):
        for vpc in self.client.describe_vpcs()['Vpcs']:
            if vpc['IsDefault']:
                return vpc['VpcId']

    def create_sg(self, name, desc, vpc_id):
        return self.client.create_security_group(GroupName=name,
                                                 Description=desc,
                                                 VpcId=vpc_id)['GroupId']

    def authorize_ingress(self, group_id, group_name, ranges):
        if not group_id:
            group_id = self.get_sg_id(group_name)
        permissions = create_permissions(ranges)
        self.client.authorize_security_group_ingress(GroupId=group_id,
                                                     GroupName=group_name,
                                                     IpPermissions=permissions)

    def revoke_ingress(self, group_id, group_name, ranges):
        permissions = create_permissions(ranges)
        self.revoke_ingress_permissions(group_id, group_name, permissions)

    def revoke_ingress_permissions(self, group_id, group_name, permissions):
        if not group_id:
            group_id = self.get_sg_id(group_name)
        preserve_default_permission(group_id, permissions)
        if not permissions:
            return
        self.client.revoke_security_group_ingress(GroupId=group_id,
                                                  GroupName=group_name,
                                                  IpPermissions=permissions)

    def delete_sg(self, group_name):
        self.client.delete_security_group(GroupName=group_name)

    def get_sg_id(self, group_name, vpc_id=None):
        if not vpc_id:
            vpc_id = self.get_default_vpc_id()
        group, = self.describe_security_groups(group_name, vpc_id)
        if group:
            return group['GroupId']

    def get_key_pairs(
            self,
            dry_run: bool = False,
            key_names: list | None = None,
            filters: list | None = None,
    ) -> dict | list[dict]:
        """
        :type dry_run: bool
        :type key_names: list
        :type filters: list
        :return:
        """
        params = dict(DryRun=dry_run)
        if key_names:
            params['KeyNames'] = key_names
        if filters:
            params['Filters'] = filters
        return self.client.describe_key_pairs(**params)

    def if_key_pair_exists(self, key_name):
        key_pairs = self.get_key_pairs().get('KeyPairs')
        if key_pairs:
            for each in key_pairs:
                if each['KeyName'] == key_name:
                    return True

    def list_vpcs(self, dry_run=None, vpc_ids=None, filters=None):
        params = dict()
        if dry_run:
            params['DryRun'] = dry_run
        if vpc_ids:
            params['VpcIds'] = vpc_ids
        if filters:
            params['Filters'] = filters
        response = self.client.describe_vpcs(**params)
        if response:
            return response['Vpcs']

    def list_subnets(self, dry_run=None, subnet_ids=None, filters=None):
        params = dict()
        if dry_run:
            params['DryRun'] = dry_run
        if subnet_ids:
            params['SubnetIds'] = subnet_ids
        if filters:
            params['Filters'] = filters
        response = self.client.describe_subnets(**params)
        if response:
            return response['Subnets']

    def get_azs(self):
        response = self.client.describe_availability_zones()
        return [az['ZoneName'] for az in response['AvailabilityZones']]

    def describe_image(self, image_id):
        params = dict(ImageIds=[image_id])
        response = self.client.describe_images(**params)
        return response['Images']

    def describe_instances(self, filters, instance_ids=None):
        params = {}
        result_list = []
        if filters:
            params['Filters'] = filters
        if instance_ids:
            params['InstanceIds'] = instance_ids
        response = self.client.describe_instances(**params)
        result_list.extend([reservation['Instances'][0]
                            for reservation in response['Reservations']])
        token = response.get('NextToken')
        while token:  # value is 'null' if there is no token
            params['NextToken'] = token
            response = self.client.describe_instances(**params)
            result_list.extend([reservation['Instances'][0]
                                for reservation in response['Reservations']])
            token = response.get('NextToken')
        return result_list

    def terminate_instances(self, instance_ids):
        self.client.terminate_instances(
            InstanceIds=instance_ids
        )

    def launch_instance(self, image_id, instance_type,
                        security_groups_names=None,
                        security_group_ids=None,
                        iam_instance_profile=None,
                        name=None, key_name=None,
                        user_data=None, tags=None,
                        subnet_id=None, availability_zone=None):

        tags = tags or []

        if iam_instance_profile:
            if not iam_instance_profile.get('Arn') \
                    and not iam_instance_profile.get('Name'):
                raise InvalidValueError(
                    f"Provided instance profile '{iam_instance_profile}'is "
                    f"not well-formed. Arn or Name nodes required."
                )

        if name:
            tags.append({
                'Key': 'Name',
                'Value': name
            })

        instance_parameters = {
            'ImageId': image_id,
            'InstanceType': instance_type,
            'MinCount': 1,
            'MaxCount': 1
        }

        if tags:
            instance_parameters['TagSpecifications'] = [{
                'ResourceType': 'instance',
                'Tags': tags
            }]

        if availability_zone:
            instance_parameters['Placement'] = {
                'AvailabilityZone': availability_zone
            }
        if key_name:
            instance_parameters['KeyName'] = key_name
        if user_data:
            instance_parameters['UserData'] = user_data
        if iam_instance_profile:
            instance_parameters['IamInstanceProfile'] = iam_instance_profile
        if subnet_id:
            instance_parameters['SubnetId'] = subnet_id
        if security_groups_names:
            instance_parameters['SecurityGroups'] = security_groups_names
        if security_group_ids:
            instance_parameters['SecurityGroupIds'] = security_group_ids

        response = self.client.run_instances(**instance_parameters)
        # always launch only one instance
        launched_instances = response['Instances']
        if len(launched_instances) < 1:
            return 'No instances launched'
        else:
            return launched_instances[0]

    def modify_instance_attribute(self, **kwargs):
        """
        log_not_found_error parameter is needed for proper log handling in the
        retry decorator
        """
        kwargs.pop('log_not_found_error', None)
        if not kwargs['InstanceId']:
            raise ParameterError('InstanceId must be specified')
        self.client.modify_instance_attribute(**kwargs)

    def deploy_security_groups(self, groups):
        default_vpc_id = self.get_default_vpc_id()
        groups_in_default_vpc = self.describe_security_groups(
            vpc_id=default_vpc_id)
        group_names = [g['GroupName'] for g in groups_in_default_vpc]

        verify = []
        create = []
        for group in groups:
            if group['n'] in group_names:
                verify.append(group)
            else:
                create.append(group)

        if create:
            self._create_security_groups(default_vpc_id, create)

        if verify:
            self._verify_security_groups(verify, groups_in_default_vpc)

    def _delete_security_groups(self, groups):
        vpc_id = self.client.get_default_vpc_id()
        security_groups = self.client.describe_security_groups(groups, vpc_id)
        existent_names = [sg['GroupName'] for sg in security_groups]
        for sg_name in groups:
            if sg_name not in existent_names:
                continue
            if sg_name == 'default':
                security_group, = self.client.describe_security_groups(
                    'default', vpc_id)
                self.client.revoke_ingress_permissions(group_id=None,
                                                       group_name='default',
                                                       permissions=
                                                       security_group[
                                                           'IpPermissions'])
            else:
                self.client.delete_sg(sg_name)

    def _create_security_groups(self, vpc_id, groups_to_create):
        for group in groups_to_create:
            if group['n'] == 'default':
                continue
            group_id = self.create_sg(group['n'], group['d'], vpc_id)
            ranges = group['r']
            # add waiting to auth sg
            time.sleep(5)
            self.authorize_ingress(group_id, group['n'], ranges)

    def _verify_security_groups(self, groups, sgs):
        security_groups = {sg['GroupName']: sg for sg in sgs}

        for group in groups:
            name = group['n']
            sg = security_groups[name]
            should_be = group['r']
            actual = []

            for permission in sg['IpPermissions']:
                for ip_range in permission['IpRanges']:
                    actual.append(ip_range['CidrIp'])

            to_revoke = [cidr for cidr in actual if cidr not in should_be]
            to_authorize = [cidr for cidr in should_be if cidr not in actual]

            if to_revoke:
                self.revoke_ingress(sg['GroupId'], name, to_revoke)
            if to_authorize:
                # add waiting to auth sg
                time.sleep(5)
                self.authorize_ingress(sg['GroupId'], name,
                                       to_authorize)

    def associate_address(self, instance_id=None, public_ip=None,
                          allow_reassociation=False):
        params = dict(AllowReassociation=allow_reassociation)
        if instance_id:
            params['InstanceId'] = instance_id
        if public_ip:
            params['PublicIp'] = public_ip
        return self.client.associate_address(**params)

    def resolve_resource_tags(  # noqa Reason: @apply_methods_decorator(retry())
            self,
            resource_tags: dict[str, dict[str, str]],
    ) -> list[dict | None]:
        base_error_message = (
            "Failed to process 'resource_tags' for the EC2 launch template. "
            "This step will be skipped."
        )
        if not isinstance(resource_tags, dict):
            _LOG.error(
                f"{base_error_message} Reason: 'resource_tags' should be a "
                f"dictionary."
            )
            return []

        resource_tag_specs = []
        for resource_type, tags_dict in resource_tags.items():
            if not isinstance(tags_dict, dict):
                _LOG.error(
                    f"{base_error_message} The value for key '{resource_type}' "
                    f"is not a dictionary as expected"
                )
                return []
            if resource_type not in EC2_LT_RESOURCE_TAGS:
                _LOG.error(
                    f"{base_error_message} "
                    f"Encountered an invalid resource type '{resource_type}'. "
                    f"Valid types include: {EC2_LT_RESOURCE_TAGS}"
                )
                return []

            tag_list = [{'Key': k, 'Value': v} for k, v in tags_dict.items()]
            resource_tag_specs.append({
                'ResourceType': resource_type,
                'Tags': tag_list,
            })

        return resource_tag_specs

    def create_launch_template(
            self,
            name: str,
            lt_data: dict,
            version_description: str | None = None,
            tags: list[dict[str, Any]] | None = None,
            resource_tags: dict[str, dict[str, str]] | None = None,
    ) -> dict:
        params = {
            'LaunchTemplateName': name,
            'LaunchTemplateData': lt_data,
        }
        if version_description is not None:
            params['VersionDescription'] = version_description
        if tags:
            params['TagSpecifications'] = [{
                'ResourceType': 'launch-template',
                'Tags': tags,
            }]
        if resource_tags:
            resource_tag_specs = self.resolve_resource_tags(resource_tags)
            if 'TagSpecifications' not in lt_data:
                lt_data['TagSpecifications'] = []
            lt_data['TagSpecifications'].extend(resource_tag_specs)

        return self.client.create_launch_template(**params)

    def create_launch_template_version(
            self,
            lt_name: str | None = None,
            lt_id: str | None = None,
            source_version: str | None = None,
            lt_data: dict | None = None,
            version_description: str | None = None,
            resource_tags: dict[str, dict[str, str]] | None = None,
    ) -> dict | None:
        if not lt_name and not lt_id:
            _LOG.error(
                'A launch template version cannot be created without the name '
                'or ID of the launch template'
            )
            return None

        params = {
            'LaunchTemplateId': lt_id or None,
            'LaunchTemplateName': lt_name if not lt_id else None,
            'SourceVersion': source_version or None,
            'VersionDescription': version_description or None,
            'LaunchTemplateData': lt_data or {},
        }
        if lt_name and lt_id:
            _LOG.warning(
                'Both the launch template name and ID are specified. The '
                'request will be made by ID'
            )
        if resource_tags:
            resource_tag_specs = self.resolve_resource_tags(resource_tags)
            if 'TagSpecifications' not in lt_data:
                lt_data['TagSpecifications'] = []
            lt_data['TagSpecifications'].extend(resource_tag_specs)

        return self.client.create_launch_template_version(
            **{k: v for k, v in params.items() if v is not None}
        )

    def describe_launch_templates(
            self,
            lt_name: str | None = None,
            lt_id = None,
    ) -> list:
        result_list = list()
        params = dict()
        if lt_name is not None and lt_id is not None:
            _LOG.warning('Both the launch template name and ID are specified. '
                         'The request will be made by ID.')
            if isinstance(lt_id, list):
                params['LaunchTemplateIds'] = lt_id
            elif isinstance(lt_id, str):
                params['LaunchTemplateIds'] = [lt_id]
            else:
                _LOG.warning(
                    f'Unsupported launch template ID type {type(lt_id)}')

        elif lt_name is not None:
            if isinstance(lt_name, list):
                params['LaunchTemplateNames'] = lt_name
            elif isinstance(lt_name, str):
                params['LaunchTemplateNames'] = [lt_name]
            else:
                _LOG.warning(
                    f'Unsupported launch template name type {type(lt_name)}')

        elif lt_id is not None:
            if isinstance(lt_id, list):
                params['LaunchTemplateIds'] = lt_id
            elif isinstance(lt_id, str):
                params['LaunchTemplateIds'] = [lt_id]
            else:
                _LOG.warning(
                    f'Unsupported launch template ID type {type(lt_id)}')
        try:
            response = self.client.describe_launch_templates(**params) if (
                params) else self.client.describe_launch_templates()
            token = response.get('NextToken')
            result_list.extend(response['LaunchTemplates'])
            while token:
                if params:
                    params['NextToken'] = token
                    response = self.client.describe_launch_templates(**params)
                else:
                    response = self.client.describe_launch_templates()
                token = response.get('NextToken')
                result_list.extend(response['LaunchTemplates'])
        except ClientError as e:
            if ('InvalidLaunchTemplateName.NotFoundException' in str(e) or
                    'InvalidLaunchTemplateId.NotFound' in str(e)):
                dynamic_message = f"by name '{lt_name}'" if lt_name else \
                    f"by ID '{lt_id}'"
                _LOG.warning(f"Launch template not found by {dynamic_message}")
            else:
                raise e
        return result_list

    def delete_launch_template(
            self,
            lt_name = None,
            lt_id = None,
            log_not_found_error: bool = True,
    ) -> None:
        """
        log_not_found_error parameter is needed for proper log handling in the
        retry decorator
        """
        params = dict()
        if lt_name is not None and lt_id is not None:
            _LOG.warning(
                'Both the launch template name and ID are specified. The '
                'request will be made by ID.'
            )
            params['LaunchTemplateId'] = lt_id

        elif lt_name is not None:
            params['LaunchTemplateName'] = lt_name

        elif lt_id is not None:
            params['LaunchTemplateId'] = lt_id
        else:
            raise ParameterError(
                'Either the launch template name or ID must be provided for '
                'removing the launch template.')
        self.client.delete_launch_template(**params)

    def modify_launch_template(
            self,
            default_version,
            lt_name=None,
            lt_id=None,
    ) -> None:
        params = dict()
        params['DefaultVersion'] = default_version

        if lt_name is not None and lt_id is not None:
            _LOG.warning(
                'Both the launch template name and ID are specified. The '
                'request will be made by ID.'
            )
            params['LaunchTemplateId'] = lt_id

        elif lt_name is not None:
            params['LaunchTemplateName'] = lt_name

        elif lt_id is not None:
            params['LaunchTemplateId'] = lt_id

        else:
            _LOG.error('A launch template modification can not be done '
                       'without the name or ID of the launch template.')
            return
        return self.client.modify_launch_template(**params)

    def get_instance_types(self, current_generation: Optional[bool] = None,
                           arch: Optional[List] = None
                           ) -> Generator[str, None, None]:

        def instance_types():
            filters = []
            if isinstance(current_generation, bool):
                filters.append({
                    'Name': 'current-generation',
                    'Values': [str(current_generation).lower()]
                })
            if isinstance(arch, list):
                assert set(arch).issubset({'arm64', 'i386', 'x86_64'})
                filters.append({
                    'Name': 'processor-info.supported-architecture',
                    'Values': arch
                })

            params = {}
            if filters:
                params['Filters'] = filters

            while True:
                res = self.client.describe_instance_types(**params)
                yield from (item['InstanceType'] for item in
                            res['InstanceTypes'])
                _next = res.get('NextToken')
                if not _next:
                    break
                params['NextToken'] = _next

        emitted = set()
        for instance_type in instance_types():
            group = instance_type.split('.')[0]
            if group not in emitted:
                yield group
                emitted.add(group)
            yield instance_type
