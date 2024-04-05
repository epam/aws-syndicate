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
from boto3 import client
from botocore.exceptions import ClientError

from syndicate.commons.log_helper import get_logger
from syndicate.connection.helper import apply_methods_decorator, retry

_LOG = get_logger('syndicate.connection.beanstalk_connection')


@apply_methods_decorator(retry())
class BeanstalkConnection(object):
    """ Elastic Beanstalk connection class."""

    def __init__(self, region=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None):
        self.client = client('elasticbeanstalk', region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)
        _LOG.debug('Opened new Elastic beanstalk connection.')

    def create_application(self, app_name, description=''):
        self.client.create_application(
            ApplicationName=app_name,
            Description=description
        )

    def remove_app(self, app_name, terminate_env_force=True):
        return self.client.delete_application(
            ApplicationName=app_name,
            TerminateEnvByForce=terminate_env_force
        )

    def create_environment(self, app_name, env_name, group_name=None,
                           description=None, cname_prefix=None, tier=None,
                           tags=None, version_label=None, template_name=None,
                           solution_stack_name=None, option_settings=None,
                           options_to_remove=None):
        """
        http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options-general.html
        :type app_name: str
        :type env_name: str
        :type group_name: str
        :type description: str
        :type cname_prefix: str
        :type tier: dict
        :param tier: { 'Name': 'string',
                       'Type': 'string',
                       'Version': 'string' }
        :type tags: list of dicts
        :param tags: [{ 'Key': 'string', 'Value': 'string' }]
        :type version_label: str
        :type template_name: str
        :type solution_stack_name: str
        :type option_settings: list of dicts
        :param option_settings: [{
                                    'ResourceName': 'string',
                                    'Namespace': 'string',
                                    'OptionName': 'string',
                                    'Value': 'string'
                                }]
        :type options_to_remove: list of dicts
        :param options_to_remove: [{
                                    'ResourceName': 'string',
                                    'Namespace': 'string',
                                    'OptionName': 'string'
                                    }]
        """
        params = dict(ApplicationName=app_name, EnvironmentName=env_name)
        if group_name:
            params['GroupName'] = group_name
        if description:
            params['Description'] = description
        if cname_prefix:
            params['CNAMEPrefix'] = cname_prefix
        if tier:
            params['Tier'] = tier
        if tags:
            params['Tags'] = tags
        if version_label:
            params['VersionLabel'] = version_label
        if template_name:
            params['TemplateName'] = template_name
        if solution_stack_name:
            params['SolutionStackName'] = solution_stack_name
        if option_settings:
            params['OptionSettings'] = option_settings
        if options_to_remove:
            params['OptionsToRemove'] = options_to_remove
        return self.client.create_environment(**params)

    def get_settings(self, app_name, template_name=None, env_name=None):
        """ You must specify either template_name or a env_name.

        :type app_name: str
        :type template_name: str
        :type env_name: str
        :return: response
        """
        params = dict(ApplicationName=app_name)
        if template_name:
            params['TemplateName'] = template_name
        if env_name:
            params['EnvironmentName'] = env_name
        return self.client.describe_configuration_settings(**params)

    def create_app_version(self, app_name, version_label, s3_bucket, s3_key):
        return self.client.create_application_version(
            ApplicationName=app_name,
            VersionLabel=version_label,
            SourceBundle={
                'S3Bucket': s3_bucket,
                'S3Key': s3_key
            }
        )

    def describe_applications(self, app_names=None):
        """
        :type app_names: list
        :return:
        """
        try:
            if app_names is None:
                app_names = []
            return self.client.describe_applications(
                ApplicationNames=app_names).get('Applications')
        except ClientError as e:
            if 'ResourceNotFoundException' in str(e):
                pass  # valid exception
            else:
                raise e

    def describe_environment_health(self, env_name, env_id=None,
                                    attr_names=None):
        """
        :type env_name: str
        :type env_id: str
        :type attr_names: list
        :param attr_names: 'Status' | 'Color' | 'Causes' | 'ApplicationMetrics'
        | 'InstancesHealth' | 'All' | 'HealthStatus' | 'RefreshedAt'
        :return: response
        """
        params = dict(EnvironmentName=env_name)
        if env_id:
            params['EnvironmentId'] = env_id
        if attr_names:
            params['AttributeNames'] = attr_names
        return self.client.describe_environment_health(**params)

    def deploy_env_version(self, app_name, env_name, version_label):
        return self.client.update_environment(ApplicationName=app_name,
                                              EnvironmentName=env_name,
                                              VersionLabel=version_label)

    def describe_available_solutions_stack_names(self):
        solution_stacks = self.client.list_available_solution_stacks()
        if solution_stacks:
            return solution_stacks['SolutionStacks']
