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
from syndicate.exceptions import ParameterError


def assert_required_property(resource_name, property_name, property_value,
                             error_msg=None):
    if property_value is None:
        error_msg = error_msg if error_msg else (
            f"Property '{property_name}' of resource '{resource_name}' is "
            f"required but absent"
        )
        raise ParameterError(error_msg)
