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
import json

from syndicate.core.conf.validator import LAMBDAS_ALIASES_NAME_CFG
from syndicate.core.generators import (_alias_variable,
                                       FILE_LAMBDA_HANDLER_NODEJS)

POLICY_LAMBDA_BASIC_EXECUTION = "lambda-basic-execution"

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name

SRC_MAIN_JAVA = 'jsrc/main/java'
FILE_POM = 'pom.xml'
CANCEL_MESSAGE = 'Creating of {} has been canceled.'

JAVA_LAMBDA_HANDLER_CLASS = """package {java_package_name};

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;

import java.util.HashMap;
import java.util.Map;

@LambdaHandler(lambdaName = "{lambda_name}",
	roleName = "{lambda_role_name}",
	isPublishVersion = true,
	aliasName = "${lambdas_alias_name}"
)
public class {lambda_class_name} implements RequestHandler<Object, Map<String, Object>> {

	public Map<String, Object> handleRequest(Object request, Context context) {
		System.out.println("Hello from lambda");
		Map<String, Object> resultMap = new HashMap<String, Object>();
		resultMap.put("statusCode", 200);
		resultMap.put("body", "Hello from Lambda");
		return resultMap;
	}
}
"""

JAVA_ROOT_POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{project_name}-group</groupId>
    <artifactId>{project_name}</artifactId>
    <version>1.0.0</version>

    <properties>
        <maven-shade-plugin.version>3.2.0</maven-shade-plugin.version>
        <deployment-configuration-annotations.version>1.10.0</deployment-configuration-annotations.version>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <src.dir>jsrc/main/java</src.dir>
    </properties>

    <dependencies>
        <!-- AWS dependencies-->
        <dependency>
            <groupId>com.amazonaws</groupId>
            <artifactId>aws-lambda-java-core</artifactId>
            <version>1.2.0</version>
        </dependency>
        <!--Syndicate annotations-->
        <dependency>
            <groupId>net.sf.aws-syndicate</groupId>
            <artifactId>deployment-configuration-annotations</artifactId>
            <version>${deployment-configuration-annotations.version}</version>
        </dependency>
    </dependencies>

    <build>
        <sourceDirectory>${src.dir}</sourceDirectory>
        <plugins>
            <plugin>
                <groupId>net.sf.aws-syndicate</groupId>
                <artifactId>deployment-configuration-maven-plugin</artifactId>
                <version>${deployment-configuration-annotations.version}</version>
                <configuration>
                    <packages>
                        <!--packages to scan-->
                    </packages>
                    <fileName>${project.name}-${project.version}.jar</fileName>
                </configuration>
                <executions>
                    <execution>
                        <id>generate-config</id>
                        <phase>compile</phase>
                        <inherited>false</inherited>
                        <goals>
                            <goal>gen-deployment-config</goal>
                            <goal>assemble-lambda-layer-files</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>${maven-shade-plugin.version}</version>
                <configuration>
                    <filters>
                        <filter>
                            <artifact>*:*</artifact>
                            <excludes>
                                <exclude>META-INF/*.SF</exclude>
                                <exclude>META-INF/*.DSA</exclude>
                                <exclude>META-INF/*.RSA</exclude>
                            </excludes>
                        </filter>
                    </filters>
                    <createDependencyReducedPom>false</createDependencyReducedPom>
                </configuration>
                <executions>
                    <execution>
                        <phase>package</phase>
                        <goals>
                            <goal>shade</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>

</project>
"""

PYTHON_LAMBDA_HANDLER_TEMPLATE = """from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger('LambdaName-handler')


class LambdaName(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass
        
    def handle_request(self, event, context):
        \"\"\"
        Explain incoming event here
        \"\"\"
        # todo implement business logic
        return 200
    

HANDLER = LambdaName()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)
"""

NODEJS_LAMBDA_HANDLER_TEMPLATE = """exports.handler = async (event) => {
    // TODO implement
    const response = {
        statusCode: 200,
        body: JSON.stringify('Hello from Lambda!'),
    };
    return response;
};
"""

GITIGNORE_CONTENT = """.syndicate
logs/
"""

CHANGELOG_TEMPLATE = """# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - yyyy-MM-dd
### Added
    -  Added items

### Changed
    -  Changed items 

### Removed
    -  Removed items 
"""

README_TEMPLATE = """# project_name

High level project overview - business value it brings, non-detailed technical overview.

### Notice
All the technical details described below are actual for the particular
version, or a range of versions of the software.
### Actual for versions: 1.0.0

## project_name diagram

![project_name](pics/project_name_diagram.png)

## Lambdas descriptions

### Lambda `lambda-name`
Lambda feature overview.

### Required configuration
#### Environment variables
* environment_variable_name: description

#### Trigger event
```buildoutcfg
{
    "key": "value",
    "key1": "value1",
    "key2": "value3"
}
```
* key: [Required] description of key
* key1: description of key1

#### Expected response
```buildoutcfg
{
    "status": 200,
    "message": "Operation succeeded"
}
```
---

## Deployment from scratch
1. action 1 to deploy the software
2. action 2
...

"""

ABSTRACT_LAMBDA_CONTENT = """from abc import abstractmethod

from commons import ApplicationException, build_response
from commons.log_helper import get_logger

_LOG = get_logger('abstract-lambda')


class AbstractLambda:

    @abstractmethod
    def validate_request(self, event) -> dict:
        \"\"\"
        Validates event attributes
        :param event: lambda incoming event
        :return: dict with attribute_name in key and error_message in value
        \"\"\"
        pass

    @abstractmethod
    def handle_request(self, event, context):
        \"\"\"
        Inherited lambda function code
        :param event: lambda event
        :param context: lambda context
        :return:
        \"\"\"
        pass

    def lambda_handler(self, event, context):
        try:
            _LOG.debug(f'Request: {event}')
            if event.get('warm_up'):
                return
            errors = self.validate_request(event=event)
            if errors:
                return build_response(code=400,
                                      content=errors)
            execution_result = self.handle_request(event=event,
                                                   context=context)
            _LOG.debug(f'Response: {execution_result}')
            return execution_result
        except ApplicationException as e:
            _LOG.error(f'Error occurred; Event: {event}; Error: {e}')
            return build_response(code=e.code,
                                  content=e.content)
        except Exception as e:
            _LOG.error(
                f'Unexpected error occurred; Event: {event}; Error: {e}')
            return build_response(code=500,
                                  content='Internal server error')
"""

INIT_CONTENT = """from commons.exception import ApplicationException

RESPONSE_BAD_REQUEST_CODE = 400
RESPONSE_UNAUTHORIZED = 401
RESPONSE_FORBIDDEN_CODE = 403
RESPONSE_RESOURCE_NOT_FOUND_CODE = 404
RESPONSE_OK_CODE = 200
RESPONSE_INTERNAL_SERVER_ERROR = 500
RESPONSE_NOT_IMPLEMENTED = 501
RESPONSE_SERVICE_UNAVAILABLE_CODE = 503


def build_response(content, code=200):
    if code == RESPONSE_OK_CODE:
        return {
            'code': code,
            'body': content
        }
    raise ApplicationException(
        code=code,
        content=content
    )


def raise_error_response(code, content):
    raise ApplicationException(code=code, content=content)
"""

EXCEPTION_CONTENT = """class ApplicationException(Exception):

    def __init__(self, code, content):
        self.code = code
        self.content = content

    def __str__(self):
        return f'{self.code}:{self.content}'
"""

LOG_HELPER_CONTENT = """import logging
import os
from sys import stdout

_name_to_level = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}

logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler(stream=stdout)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(console_handler)


log_level = _name_to_level.get(os.environ.get('log_level'))
if not log_level:
    log_level = logging.INFO
logging.captureWarnings(True)


def get_logger(log_name, level=log_level):
    module_logger = logger.getChild(log_name)
    if level:
        module_logger.setLevel(level)
    return module_logger
"""

PYTHON_TESTS_INIT_CONTENT = \
"""import sys
from pathlib import Path

SOURCE_FOLDER = 'src'


class ImportFromSourceContext:
    \"\"\"Context object to import lambdas and packages. It's necessary because
    root path is not the path to the syndicate project but the path where
    lambdas are accumulated - SOURCE_FOLDER \"\"\"

    def __init__(self, source_folder=SOURCE_FOLDER):
        self.source_folder = source_folder
        self.assert_source_path_exists()

    @property
    def project_path(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def source_path(self) -> Path:
        return Path(self.project_path, self.source_folder)

    def assert_source_path_exists(self):
        source_path = self.source_path
        if not source_path.exists():
            print(f'Source path "{source_path}" does not exist.',
                  file=sys.stderr)
            sys.exit(1)

    def _add_source_to_path(self):
        source_path = str(self.source_path)
        if source_path not in sys.path:
            sys.path.append(source_path)

    def _remove_source_from_path(self):
        source_path = str(self.source_path)
        if source_path in sys.path:
            sys.path.remove(source_path)

    def __enter__(self):
        self._add_source_to_path()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_source_from_path()

"""

PYTHON_TESTS_INIT_LAMBDA_TEMPLATE = \
"""import unittest
import importlib
from tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module('lambdas.{lambda_name}.handler')


class {camel_lambda_name}LambdaTestCase(unittest.TestCase):
    \"\"\"Common setups for this lambda\"\"\"

    def setUp(self) -> None:
        self.HANDLER = LAMBDA_HANDLER.{camel_lambda_name}()

"""

PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE = \
"""from tests.{test_lambda_folder} import {camel_lambda_name}LambdaTestCase


class TestSuccess({camel_lambda_name}LambdaTestCase):

    def test_success(self):
        self.assertEqual(self.HANDLER.handle_request(dict(), dict()), 200)

"""


def _stringify(dict_content):
    return json.dumps(dict_content, indent=2)


def _generate_python_node_lambda_config(lambda_name, lambda_relative_path):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'handler.lambda_handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': 'python3.10',
        'memory': 128,
        'timeout': 100,
        'lambda_path': lambda_relative_path,
        'dependencies': [],
        'event_sources': [],
        'env_variables': {},
        'publish_version': True,
        'alias': _alias_variable(LAMBDAS_ALIASES_NAME_CFG),
        'url_config': {},
        'ephemeral_storage': 512,
        # 'platforms': ['manylinux2014_x86_64']
        # by default (especially if you have linux), you don't need it
    })


def _generate_nodejs_node_lambda_config(lambda_name, lambda_relative_path):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'index.handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': 'nodejs14.x',
        'memory': 128,
        'timeout': 100,
        'lambda_path': lambda_relative_path,
        'dependencies': [],
        'event_sources': [],
        'env_variables': {},
        'publish_version': True,
        'alias': _alias_variable(LAMBDAS_ALIASES_NAME_CFG),
        'url_config': {},
        'ephemeral_storage': 512
    })


def _generate_package_nodejs_lambda(lambda_name):
    return _stringify({
        "name": lambda_name,
        "version": "1.0.0",
        "description": "",
        "main": FILE_LAMBDA_HANDLER_NODEJS,
        "scripts": {},
        "author": "",
        "license": "ISC",
        "dependencies": {
        }
    })


def _generate_package_lock_nodejs_lambda(lambda_name):
    return _stringify({
        "name": lambda_name,
        "version": "1.0.0",
        "lockfileVersion": 1,
        "requires": True,
        "dependencies": {}
    })


def _get_lambda_default_policy():
    return _stringify({
        POLICY_LAMBDA_BASIC_EXECUTION: {
            'policy_content': {
                "Statement": [
                    {
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "dynamodb:GetItem",
                            "dynamodb:Query",
                            "dynamodb:PutItem",
                            "dynamodb:Batch*",
                            "dynamodb:DeleteItem",
                            "ssm:PutParameter",
                            "ssm:GetParameter",
                            "kms:Decrypt"
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ],
                "Version": "2012-10-17"},
            "resource_type": "iam_policy"
        }
    })


def _generate_lambda_role_config(role_name, stringify=True):
    role_content = {
        role_name: {
            "predefined_policies": [],
            "principal_service": "lambda",
            "custom_policies": [
                POLICY_LAMBDA_BASIC_EXECUTION
            ],
            "resource_type": "iam_role",
            "allowed_accounts": [
                "${account_id}"
            ]
        }
    }
    return _stringify(role_content) if stringify else role_content
