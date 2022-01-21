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


def build_terraform_resource_name(*args):
    res_name = []
    for arg in args:
        if arg:
            res_name.append(arg[0].upper() + arg[1:])
    return ''.join(res_name)


def lambda_layer_name(layer_name):
    return build_terraform_resource_name(layer_name, 'layer')
