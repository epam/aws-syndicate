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

from syndicate.core.conf.validator import (
    LAMBDAS_ALIASES_NAME_CFG, LOGS_EXPIRATION
)
from syndicate.core.generators import (_alias_variable,
                                       FILE_LAMBDA_HANDLER_NODEJS)
from syndicate.core.groups import DEFAULT_RUNTIME_VERSION, RUNTIME_PYTHON, \
    RUNTIME_NODEJS, RUNTIME_DOTNET, PYTHON_ROOT_DIR_PYAPP
from syndicate.core.constants import DEFAULT_JSON_INDENT

POLICY_LAMBDA_BASIC_EXECUTION = "lambda-basic-execution"

LAMBDA_ROLE_NAME_PATTERN = '{0}-role'  # 0 - lambda_name

SRC_MAIN_JAVA = 'src/main/java'
FILE_POM = 'pom.xml'
CANCEL_MESSAGE = 'Creating of {} has been canceled.'

JAVA_TAGS_IMPORT = """
import com.syndicate.deployment.annotations.tag.Tag;
import com.syndicate.deployment.annotations.tag.Tags;"""

JAVA_TAGS_ANNOTATION_TEMPLATE = """
@Tags(value = {
{tags}})
"""

JAVA_TAG_ANNOTATION_TEMPLATE = '    @Tag(key = "{key}", value = "{value}")'

JAVA_LAMBDA_HANDLER_CLASS = """package {java_package_name};

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;{tags_import}
import com.syndicate.deployment.model.RetentionSetting;

import java.util.HashMap;
import java.util.Map;
{tags}
@LambdaHandler(
    lambdaName = "{lambda_name}",
	roleName = "{lambda_role_name}",
	isPublishVersion = true,
	aliasName = "${lambdas_alias_name}",
	logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
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
        <maven-shade-plugin.version>3.5.2</maven-shade-plugin.version>
        <syndicate.java.plugin.version>1.17.1</syndicate.java.plugin.version>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <src.dir>src/main/java</src.dir>
        <resources.dir>src/main/resources</resources.dir>
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
            <version>${syndicate.java.plugin.version}</version>
        </dependency>
    </dependencies>

    <build>
        <sourceDirectory>${src.dir}</sourceDirectory>
        <resources>
            <resource>
                <directory>${resources.dir}</directory>
            </resource>
        </resources>        
        <plugins>
            <plugin>
                <groupId>net.sf.aws-syndicate</groupId>
                <artifactId>deployment-configuration-maven-plugin</artifactId>
                <version>${syndicate.java.plugin.version}</version>
                <configuration>
                    <packages>
                        <!--packages to scan-->
                        <package>{java_package_name}</package>
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

_LOG = get_logger(__name__)


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

DOTNET_LAMBDA_HANDLER_TEMPLATE = """using System.Collections.Generic;
using Amazon.Lambda.Core;
using Amazon.Lambda.APIGatewayEvents;

[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.SystemTextJson.DefaultLambdaJsonSerializer))]

namespace SimpleLambdaFunction;

public class Function
{
    public APIGatewayProxyResponse FunctionHandler(APIGatewayProxyRequest request, ILambdaContext context)
    {
        return new APIGatewayProxyResponse
        {
            StatusCode = 200,
            Body = "Hello world!",
            Headers = new Dictionary<string, string> { { "Content-Type", "text/plain" } }
        };
    }
}
"""

DOTNET_LAMBDA_CSPROJ_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">

    <PropertyGroup>
		<AssemblyName>SimpleLambdaFunction</AssemblyName>
        <TargetFramework>net8.0</TargetFramework>
        <OutputType>Library</OutputType>
        <Nullable>enable</Nullable>
        <GenerateRuntimeConfigurationFiles>true</GenerateRuntimeConfigurationFiles>
    </PropertyGroup>

    <ItemGroup>
        <PackageReference Include="Amazon.Lambda.APIGatewayEvents" Version="2.4.0" />
        <PackageReference Include="Amazon.Lambda.Core" Version="2.2.0" />
        <PackageReference Include="Amazon.Lambda.Serialization.SystemTextJson" Version="2.2.0" />
    </ItemGroup>

</Project>
"""

DOTNET_LAMBDA_LAYER_CSPROJ_TEMPLATE = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <!-- Layer packages here -->
    <PackageReference Include="Amazon.Lambda.Core" Version="2.2.0" />
  </ItemGroup>
</Project>

'''

GITIGNORE_CONTENT = """.syndicate
logs/
.syndicate-config-*/
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

_LOG = get_logger(__name__)


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

INIT_CONTENT = """from commons.exceptions import ApplicationException

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
f"""import unittest
import importlib
from {PYTHON_ROOT_DIR_PYAPP}.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module('lambdas.{{lambda_name}}.handler')


class {{camel_lambda_name}}LambdaTestCase(unittest.TestCase):
    \"\"\"Common setups for this lambda\"\"\"

    def setUp(self) -> None:
        self.HANDLER = LAMBDA_HANDLER.{{camel_lambda_name}}()

"""

PYTHON_TESTS_BASIC_TEST_CASE_TEMPLATE = \
f"""from {PYTHON_ROOT_DIR_PYAPP}.tests.{{test_lambda_folder}} import {{camel_lambda_name}}LambdaTestCase


class TestSuccess({{camel_lambda_name}}LambdaTestCase):

    def test_success(self):
        self.assertEqual(self.HANDLER.handle_request(dict(), dict()), 200)

"""

S3_BUCKET_WEBSITE_HOSTING_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "WebSiteHostingGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::{bucket_name}/*"
            ],
            "Condition": {
                "IpAddress": {
                    "aws:SourceIp": [
                        "XXX.XXX.XXX.XXX/32"
                    ]
                }
            }
        }
    ]
}

SWAGGER_UI_INDEX_FILE_CONTENT = \
    """<!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta
          name="description"
          content="SwaggerUI"
        />
        <title>SwaggerUI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
      </head>
      <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js" crossorigin></script>
      <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-standalone-preset.js" crossorigin></script>
      <script>
        window.onload = () => {
          window.ui = SwaggerUIBundle({
            url: './spec_file_name',
            dom_id: '#swagger-ui',
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            layout: "StandaloneLayout",
          });
        };
      </script>
      </body>
    </html>"""

REQUIREMENTS_FILE_CONTENT = '# list of requirements'
LOCAL_REQUIREMENTS_FILE_CONTENT = '# local requirements'


def _stringify(dict_content):
    return json.dumps(dict_content, indent=DEFAULT_JSON_INDENT)


def _generate_python_node_lambda_config(lambda_name, lambda_relative_path,
                                        tags):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'handler.lambda_handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': DEFAULT_RUNTIME_VERSION[RUNTIME_PYTHON],
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
        'logs_expiration': _alias_variable(LOGS_EXPIRATION),
        'tags': tags
        # 'platforms': ['manylinux2014_x86_64']
        # by default (especially if you have linux), you don't need it
    })


def _generate_python_node_layer_config(layer_name, runtime):
    layer_template = {
        "name": layer_name,
        "resource_type": "lambda_layer",
        "runtimes": [
            DEFAULT_RUNTIME_VERSION.get(runtime)
        ],
        "deployment_package": f"{layer_name}_layer.zip"
    }
    if runtime in DEFAULT_RUNTIME_VERSION[RUNTIME_DOTNET]:
        layer_template["custom_packages"] = []
    return _stringify(layer_template)


def _generate_node_layer_package_file(layer_name):
    return _stringify({
        "name": layer_name,
        "version": "1.0.0",
        "description": "",
        "main": "index.js",
        "scripts": {},
        "author": "",
        "license": "ISC",
        "dependencies": {}
    })


def _generate_node_layer_package_lock_file(layer_name):
    return _stringify({
        "name": layer_name,
        "version": "1.0.0",
        "lockfileVersion": 1,
        "requires": True,
        "dependencies": {}
    })


def _generate_nodejs_node_lambda_config(lambda_name, lambda_relative_path,
                                        tags):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': f'lambdas/{lambda_name}/index.handler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': DEFAULT_RUNTIME_VERSION[RUNTIME_NODEJS],
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
        'tags': tags
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


def _generate_dotnet_lambda_config(lambda_name, lambda_relative_path, tags):
    return _stringify({
        'version': '1.0',
        'name': lambda_name,
        'func_name': 'SimpleLambdaFunction::SimpleLambdaFunction.Function::FunctionHandler',
        'resource_type': 'lambda',
        'iam_role_name': LAMBDA_ROLE_NAME_PATTERN.format(lambda_name),
        'runtime': DEFAULT_RUNTIME_VERSION[RUNTIME_DOTNET],
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
        'tags': tags
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
            "resource_type": "iam_policy",
            "tags": {}
        }
    })


def _generate_lambda_role_config(role_name, tags, stringify=True):
    role_content = {
        role_name: {
            "predefined_policies": [],
            "principal_service": "lambda",
            "custom_policies": [
                POLICY_LAMBDA_BASIC_EXECUTION
            ],
            "resource_type": "iam_role",
            "tags": tags
        }
    }
    return _stringify(role_content) if stringify else role_content


def _generate_swagger_ui_config(resource_name, path_to_spec, target_bucket):
    return _stringify({
        "name": resource_name,
        "resource_type": "swagger_ui",
        "path_to_spec": path_to_spec,
        "target_bucket": target_bucket
    })


def _generate_syncapp_config(resource_name, schema_file_name, tags=None):
    config_content = {
        "name": resource_name,
        "resource_type": "appsync",
        "primary_auth_type": "API_KEY",
        "api_key_expiration_days": 7,
        "schema_path": schema_file_name,
        "data_sources": [],
        "resolvers": [],
        "functions": [],
        "log_config": {
            "logging_enabled": False,
            "field_log_level": "ERROR",
            "cloud_watch_logs_role_name": '',
            'exclude_verbose_content': False
        },
        "tags": tags or {},
    }
    return _stringify(config_content)


def _generate_syncapp_default_schema():
    content = '''# Define the structure of your API with the GraphQL
# schema definition language (SDL) here.

type Query {
	test: String
}

schema {
	query: Query
}
    '''
    return content


def _generate_syncapp_js_resolver_code():
    default_code = '''/**
 * Sends a request to the attached data source
 * @param {import('@aws-appsync/utils').Context} ctx the context
 * @returns {*} the request
 */
export function request(ctx) {
    // Update with custom logic or select a code sample.
    return {};
}

/**
 * Returns the resolver result
 * @param {import('@aws-appsync/utils').Context} ctx the context
 * @returns {*} the result
 */
export function response(ctx) {
    // Update with response logic
    return ctx.result;
}
'''
    return default_code


def _generate_syncapp_vtl_resolver_req_mt(data_source_type):
    match data_source_type:
        case 'NONE':
            content = \
                '''#**Resolvers with None data sources can locally publish events that fire
                subscriptions or otherwise transform data without hitting a backend data source.
                The value of 'payload' is forwarded to $ctx.result in the response mapping template.
                *#
                {
                    "version": "2018-05-29",
                    "payload": {
                        "hello": "local",
                    }
                }
                            '''
        case 'AWS_LAMBDA':
            content = \
                '''#**The value of 'payload' after the template has been evaluated
                will be passed as the event to AWS Lambda.
                *#
                {
                  "version" : "2018-05-29",
                  "operation": "Invoke",
                  "payload": $util.toJson($context.args)
                }
                                            '''
        case 'AMAZON_DYNAMODB':
            content = \
                '''## Below example shows how to look up an item with a Primary Key of "id" from GraphQL arguments
                ## The helper $util.dynamodb.toDynamoDBJson automatically converts to a DynamoDB formatted request
                ## There is a "context" object with arguments, identity, headers, and parent field information you can access.
                ## It also has a shorthand notation available:
                ##  - $context or $ctx is the root object
                ##  - $ctx.arguments or $ctx.args contains arguments
                ##  - $ctx.identity has caller information, such as $ctx.identity.username
                ##  - $ctx.request.headers contains headers, such as $context.request.headers.xyz
                ##  - $ctx.source is a map of the parent field, for instance $ctx.source.xyz
                ## Read more: https://docs.aws.amazon.com/appsync/latest/devguide/resolver-mapping-template-reference.html
                
                {
                    "version": "2018-05-29",
                    "operation": "GetItem",
                    "key": {
                        "id": $util.dynamodb.toDynamoDBJson($ctx.args.id),
                    }
                }
                '''
        case 'PIPELINE':
            content = \
                '''## By default in a before template, all you need is a valid JSON payload.
                ## You can also stash data to be made available to the functions in the pipeline.
                ## Examples: 
                ## - $ctx.stash.put("email", $ctx.args.email)
                ## - $ctx.stash.put("badgeNumber", $ctx.args.input.badgeNumber)
                ## - $ctx.stash.put("username", $ctx.identity.username)
                
                {}
                '''
    return content


def _generate_syncapp_vtl_resolver_resp_mt(data_source_type):
    match data_source_type:
        case 'NONE':
            content = '''$util.toJson($context.result)'''
        case 'AWS_LAMBDA':
            content = '''$util.toJson($context.result)'''
        case 'AMAZON_DYNAMODB':
            content = \
                '''## Pass back the result from DynamoDB. **
                $util.toJson($ctx.result)
                '''
        case 'PIPELINE':
            content = \
                '''## The after mapping template is used to collect the final value that is returned by the resolver.
                $util.toJson($ctx.result)'''
    return content
