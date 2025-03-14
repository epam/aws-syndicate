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
from syndicate.exceptions import NotImplementedError
from .cf_resource_converter import CfResourceConverter


class CfSnsApplicationConverter(CfResourceConverter):

    def convert(self, name, meta):
        # The converter may be implemented as a custom CF resource that
        # invokes a lambda which performs a creation of an SNS application.
        raise NotImplementedError(
            'SNS platform application is not supported by CloudFormation.')
