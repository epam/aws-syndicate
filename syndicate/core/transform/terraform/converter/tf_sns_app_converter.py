"""
    Copyright 2021 EPAM Systems, Inc.

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
from syndicate.core.transform.terraform.converter.tf_resource_converter import \
    TerraformResourceConverter


class SNSApplicationConverter(TerraformResourceConverter):

    def convert(self, name, resource):
        platform = resource.get('platform')
        attributes = resource.get('attributes')
        platform_credential = attributes.get('PlatformCredential')
        platform_principal = attributes.get('PlatformPrincipal')

        app_meta = build_sns_app_meta(application_name=name, platform=platform,
                                      platform_credential=platform_credential,
                                      platform_principal=platform_principal)
        self.template.add_aws_sns_platform_application(meta=app_meta)


def build_sns_app_meta(application_name, platform, platform_credential,
                       platform_principal):
    application = {}
    if application_name:
        application.update({'name': application_name})

    if platform:
        application.update({'platform': platform})

    if platform_credential:
        application.update({'platform_credential': platform_credential})

    if platform_principal:
        application.update({'platform_principal': platform_principal})

    resource = {
        application_name: application
    }
    return resource
