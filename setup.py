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
from os import path

SYNDICATE_DESCRIPTION = ('AWS-syndicate is an Amazon Web Services deployment '
                         'framework written in Python, which allows to '
                         'easily deploy serverless applications using '
                         'resource descriptions.')


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aws-syndicate',
    version='0.9.5',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click==7.1.1',
        'botocore==1.15.3',
        'boto3==1.12.3',
        'configobj==5.0.6',
        'tqdm==4.19.5',
        'colorama==0.4.1',
        'pyyaml==5.3.1'
    ],
    entry_points='''
        [console_scripts]
        syndicate=syndicate.core.handlers:syndicate
    ''',
    url='https://github.com/epam/aws-syndicate',
    long_description=long_description,
    long_description_content_type='text/markdown',
    description=SYNDICATE_DESCRIPTION,
    author='EPAM Systems',
    author_email='support@syndicate.team',
    keywords=['AWS', 'SERVERLESS', 'CLOUD', 'LAMBDA', 'DEPLOY'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3.7'
    ],
)
