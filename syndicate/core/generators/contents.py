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

SRC_MAIN_JAVA = '/src/main/java'
FILE_POM = '/pom.xml'
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
        <deployment-configuration-annotations.version>1.5.8</deployment-configuration-annotations.version>
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

_LOG = get_logger('lambda-name-handler')

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
    HANDLER.lambda_handler(event=event, context=context)
   
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
sdct.log
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

def _stringify(dict_content):
    return json.dumps(dict_content, indent=2)


def _generate_python_node_lambda_config(lambda_name, lambda_relative_path):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'handler.lambda_handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': 'python3.7',
        'memory': 128,
        'timeout': 100,
        'lambda_path': lambda_relative_path,
        'dependencies': [],
        'event_sources': [],
        'env_variables': {},
        'publish_version': True,
        'alias': _alias_variable(LAMBDAS_ALIASES_NAME_CFG)
    })


def _generate_nodejs_node_lambda_config(lambda_name, lambda_relative_path):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'index.handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': 'nodejs10.x',
        'memory': 128,
        'timeout': 100,
        'lambda_path': lambda_relative_path,
        'dependencies': [],
        'event_sources': [],
        'env_variables': {},
        'publish_version': True,
        'alias': _alias_variable(LAMBDAS_ALIASES_NAME_CFG)
    })


def _generate_package_nodejs_lambda(lambda_name):
    return _stringify({
        "name": lambda_name,
        "version": "1.0.0",
        "description": "",
        "main": FILE_LAMBDA_HANDLER_NODEJS[1:],
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
