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
from setuptools import find_packages, setup

setup(
    name='syndicate',
    version='0.6',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click==6.7',
        'botocore==1.10.73',
        'boto3==1.7.73',
        'configobj==5.0.6',
        'requests==2.20.0',
        'tqdm==4.19.5',
        'functools32==3.2.3.post2'
    ],
    entry_points='''
        [console_scripts]
        syndicate=syndicate.core.handlers:syndicate
    ''',
)
