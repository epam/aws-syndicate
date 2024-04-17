"""
    Copyright 2024 EPAM Systems, Inc.

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

from syndicate.core.constants import \
    EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS


class LaunchTemplateValidator:
    def __init__(self, name, meta):
        self._name = name,
        self._meta = meta

    def validate(self):
        version_description = self._meta.get('version_description')
        if version_description is not None:
            if not isinstance(version_description, str):
                self._error(
                    "Unsupported type of the key 'version_description'. "
                    f"Supported type - 'str', current type - "
                    f"'{type(version_description).__name__}'")
        self._validate_lt_data(self._meta.get('launch_template_data'))

    def _error(self, message):
        raise AssertionError(message)

    def _validate_lt_data(self, lt_data):
        from syndicate.core import CONFIG
        if not lt_data:
            self._error('The launch_template_data is required.')

        if not isinstance(lt_data, dict):
            self._error(
                "Unsupported type of the key 'launch_template_data'. "
                f"Supported type - 'map', current type - "
                f"{type(lt_data).__name__}")

        imds_support = lt_data.get('imds_support')
        if imds_support is not None:
            if imds_support not in EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS:
                self._error(f"The value of 'imds_support' - '{imds_support}' "
                            f"is invalid. Currently supported version - "
                            f"{EC2_LAUNCH_TEMPLATE_SUPPORTED_IMDS_VERSIONS}")

        user_data_file_path = lt_data.get('userdata_file')
        if user_data_file_path is not None:
            if not os.path.isabs(user_data_file_path):
                user_data_file_path = os.path.join(CONFIG.project_path,
                                                   user_data_file_path)
            if not os.path.isfile(user_data_file_path):
                self._error(f"There is no user data found by path "
                            f"'{user_data_file_path}'.")


def validate_launch_template(name, meta):
    LaunchTemplateValidator(name, meta).validate()
