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
from abc import abstractmethod

from syndicate.core.transform.terraform.terraform_template import \
    TerraformTemplate


class TerraformResourceConverter:

    def __init__(self, template: TerraformTemplate, config=None,
                 resources_provider=None):
        self.template = template
        self.config = config
        self.resources_provider = resources_provider

    @abstractmethod
    def convert(self, name, resource):
        pass
