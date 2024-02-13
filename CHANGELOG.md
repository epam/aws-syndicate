# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [1.14.4] - 2024-02-13
- Actualized information in the file readme.md
- Actualized project examples

# [1.14.3] - 2024-02-09
### Added
- added missed import into the Java lambda template

# [1.14.2] - 2024-02-06
- Add `api_source_arn` when creating permission for lambda authorizer.
- Change in `syndicate generate` command default value for `lambdas_alias_name`
from `prod` to `dev`.

# [1.14.1] - 2024-02-05
- Improve the CloudWatch log groups `POSSIBLE_RETENTION_DAYS` constant to
support all values.
- Update and fix retry decorator. If the maximum number of retries is reached,
an `Exception` is thrown with a detailed description of the function that failed
and the reason.
- Refactor the Lambda SQS Trigger Creation process to check for existing event
source mapping, and update or create as needed.

# [1.14.0] - 2024-02-05
- Implemented API GateWay `Throttling` settings management

# [1.13.2] - 2024-02-05
- Added CloudWatch logs expiration management support to the Syndicate Java plugin 1.11.0

# [1.13.1] - 2024-02-01
- Lambda parameter `architecture` changed to `architectures`, and the value of the key changed to a list of string
- Change the Java plugin @LambdaHandler annotation processor to produce the parameter `architectures` instead of `architecture`

# [1.13.0] - 2024-01-31
- Add support for OpenAPI v3 deploy, update and clean-up in API Gateway
- Implement permission setting for lambda functions in OpenAPI v3 implementations

# [1.12.2] - 2024-01-31
- Added validation for the configuration parameter `iam_suffix`
- Added warning to logs in case of unknown parameters in the configuration file

# [1.12.1] - 2024-01-30
- Fixed API Gateway deployment with the default value(300) of the `Cache time to live` parameter if the specified value is `0`

# [1.12.0] - 2024-01-30
### Added
- The @LambdaHandler annotation for Java plugin improved to support the lambda 'architecture' management
- The @LambdaLayer annotation for Java plugin improved to support the lambda 'architectures' management
- The Java example 'java-layer-url' extended to use Lambda architecture management
### Changed
- The deployment-configuration-processor version bumped to 1.11.0

# [1.11.0] - 2024-01-26
- Implemented lambda function processor architecture type management
- Implemented lambda layers compatible processor architecture types management

# [1.10.2] - 2024-01-19
- Add a feature in `syndicate update` command to update `logs_expiration`
parameter in `cloudWatch` logs group. For setting `logs_expiration`, refer to
`syndicate_aliases`.

# [1.10.1] - 2024-01-17
- Change from `error` to `warning` if integer not provided in allowed values for
`logs_expiration` values and set default to `30`.

# [1.10.0] - 2024-01-16
- Add parameter `logs_expiration` to `syndicate_aliases.yml` and `lambda_config.json`. 
The default value is set to "30 days". To ensure the logs expire after 10 years,
set the value to: `logs_expiration: 0`.

# [1.9.9] - 2024-01-15
- Fix dynamodb table capacity mode recognition during update

# [1.9.8] - 2024-01-15
- Add last exception raise in `connection/helper.py:retry()`

# [1.9.7] - 2024-01-12
- Changed required type for attribute `resources_requirements` from dict to list
in `batch_jobdef_validator.py`

# [1.9.6] - 2024-01-08
- Fixed an issue related to lambda generation with a name that contains underscores

# [1.9.5] - 2023-12-21
### Changed
- conf files handling library configobj replaced with built-in configparser package

# [1.9.4] - 2023-12-18
- Fixed an issue related to s3 bucket lifecycle policy deployment
### Changed
- Updating gsi capacity units when changing table capacity mode from on-demand 
to provisioned
### Removed
- Capacity units when updating global secondary indexes when 
table capacity mode is on-demand

# [1.9.3] - 2023-12-14
### Changed
- Updating `max_retry` attribute from $LATEST lambda version to alias only 

# [1.9.2] - 2023-12-13
### Added
- Default empty value for dynamodb's global secondary indexes 
when not declared in deployment_resources.json

# [1.9.1] - 2023-12-13
### Added
- `dynamodb_table` resource priority in `UPDATE_RESOURCE_TYPE_PRIORITY` constant

# [1.9.0] - 2023-12-12
### Added
- Ability to update `dynamodb_table` resource, specifically: 
table capacity, gsi capacity, table billing mode, table ttl, add or remove gsi 

# [1.8.0] - 2023-12-12
### Added
- A new Maven plugin goal 'assemble-lambda-layer-files' has been added to the 'deployment-configuration-processor' plugin
- A new Java lambda example with assembling layer files and url config has been added
- An example of adding custom SDK to layer and url config for lambda has been added to Java examples folder
### Changed
- The deployment-configuration-processor version bumped to 1.10.0

# [1.7.5] - 2023-12-11
- Fixed API Gateway service integration credentials building

# [1.7.4] - 2023-12-08
- Fixed lambda event invoke config creating and updating

# [1.7.3] - 2023-12-07
- Fixed lambda deployment in extended prefix mode

# [1.7.2] - 2023-11-14
- Fixed SNS subscription deletion with SNS topic deletion
- Fixed processing of retries for `InvalidParameterValueException`

# [1.7.1] - 2023-11-14
- Added waiting for IAM role creation

# [1.7.0] - 2023-11-10
- Implemented extended prefix mode

# [1.6.0] - 2023-12-07
- Added `max_retries` attribute setting for creating and updating 
lambda configuration

# [1.5.0] - 2023-11-08
### Added
- LambdaUrlConfig java annotation has been added to the aws-syndicate mvn plugin.
### Changed
- deployment-configuration-processor version bumped to 1.9.0.

# [1.4.0] - 2023-09-29
- Add EventBridge Scheduler support

# [1.3.4] - 2023-09-28
- replace ignored pip install parameter `--python` with `python-version`

# [1.3.3] - 2023-09-22
- Set default lambda Python runtime to 3.10
- Updated libraries to support Python 3.10 as a development tool:
  - `boto3` from 1.26.18 to 1.26.80
  - `botocore` from 1.29.18 to 1.29.80
  - `colorama` from 0.4.1 to 0.4.5
  - `configobj` from 5.0.6 to 5.0.8
  - `pyyaml` from 5.4 to 6.0.1
  - `requests` from 2.27.1 to 2.31.0
  - `tabulate` from 0.8.9 to 0.9.0
  - `tqdm` from 4.19.5 to 4.65.2

# [1.3.2] - 2023-09-20
- Fixed ignored request parameters when creating api gateway's resource method using lambda integration

# [1.3.1] - 2023-09-20
- Add support Python 3.10 and Python 3.11

# [1.3.0] - 2023-09-14
- Added ability to use SSO credentials
- Added parameter `aws_session_token` to `sdct.conf` for role assuming

# [1.2.4] - 2023-04-13
- Added `web_socker_api_gateway` resource type. Allows to deploy web-socket
  API with lambda integrations

# [1.2.3] - 2023-05-15
- Fixed resolving of available instance types for Windows

# [1.2.2] - 2023-05-05
- Resolve available instance types from `botocore` data

# [1.2.1] - 2023-05-04
- Added new supported EC2 instance types: `c7g`, `t4g`, `t3`

# [1.2.0] - 2023-04-13
- Added `transform` command that creates a CloudFormation or Terraform template based on the `build_meta` of your project


## [1.1.1] - 2023-04-11
- improve python artifacts building process. By default, 
  `manylinux2014_x86_64` is used for M1 and Windows. In case the platform 
  is set and pip installation fails, the Syndicate will try to install 
  a package the default way.

## [1.1.0] - 2022-12-07
### Added
- `snap_start` support of Java-based lambda configurations of 
`PublishedVersions` or `None` values.
- `resourceGroup` annotation parameter to Java-based lambda.
- Specify target AWS Lambda platform, python version and implementation to install dependencies


## [1.0.0] - 2021-06-11
### Changed
- `init` command was replaced with `generate config`
- Interface of command was improved, `access_key` and `secret_key` params made optional
- Removed `account_id` param and provided ability to resolve it by STS or instance profile
- `python_build_mapping`, `java_build_mapping`, `nodejs_build_mapping` was removed as they will be resolved using the `.syndicate` file
- `generate lambda` command was improved, `common` and `tests` module for python runtime is generated with the first lambda. They contain basic common class all lambdas and simple initial test case.
- Provided ability to add information about created lambda to `.syndicate` file
- Added `test` command that allows to run tests inside your python project
- Added `profiler` command that allows to display application Lambda metrics
- Fixed an issue in `clean` command, associated with API Gateway skipping removing Lambda trigger permissions
- Fixed an issued in `clean` command associated with removing EC2 instances
- Fixed an issue in `clean` command, associated with removing resources if they specified as excluded
- Add ANY, PATCH to supported methods in API Gateway
- Changed logs format. All the logs are saved up to the path from SDCT_CONF variable if it exists. Otherwise the logs are saved to user's home directory.
- Added validation of `bundle_bucket_name` when generating config
- Added prefix and suffix validation when generating config. Their length must be less or equal to 5
- Fixed bugs with no output from `update` command
- Unified datetime format to ISO8601
- Changed `.syndicate` events saving algorithm: 30-days old events are deleted after each updating of the file. But 20 events (or less if there aren't this many) will be kept anyway, so if some amount of events exist, it isn't possible to get them all deleted.
- Added `latest_event` field to `.syndicate` file to keep the latest action's info such as: operation type, `bundle_name`, `deploy_name`, performing time and other
- Fixed generating building and deploying java and nodejs lambdas. Updated `pom.xml` template according to the new version of `deployment-configuration-annotation` plugin
- Fixed an issue when build meta is validated before resolving aliases in it
- Added `minimum_compression_size` param to API gateway deployment_resource declaration. It enables payload compression for an API with given size;
- Added lambda URL support;
- Added lambda ephemeral storage support;
- Added an ability to create DynamoDB in on-demand mode if `read_capacity` 
  and `write_capacity` are not specified;
- Describe an existing Api Gateway instead of creating a new one;
- Added an ability to create models in API Gateway;
- Added AWS Kinesis Firehose support;
- Add lambda event-source-mapping filters support;
- Added an ability to build lambda layers (similarly to lambdas)


## [0.9.6] - 2021-04-29
### Changed
- Add AWS Batch support
- Add external resources support
- Add parameter binary_media_type for API Gateway resource type

## [0.9.5] - 2021-03-11
### Changed
- Updated Python project examples
- Added integration request parameters for API Gateway
- Added request validator for API Gateway
- Fixed a lost first zero issue due to incorrect work `syndicate init` command for AWS accounts, which start at zero.
- Added the ability to add `logs_expiration` parameter in lambda_config.json.
- Update Java version in Travis builds

## [0.9.4] - 2020-10-16
### Changed
- Fixed the error related with absent parameter `session_duration` in `sdct.conf` 


## [0.9.3] - 2020-10-13
### Changed
- Added parameter `session_duration` to `sdct.conf` for setting session duration while role assuming 


## [0.9.2] - 2020-07-28
### Changed
- Fixed DynamoDB LSI check while building bundle
- Fixed deployment of CloudWatch Rules


## [0.9.1] - 2020-07-20
### Added
- Add required mark (asterisk) for required parameters in 'Help' section for `syndicate generate lambda` and `syndicate generate project` commands
- Add validation for the empty `lambda_name` parameter in `syndicate generate lambda` command

### Changed
- Removed `traceback` from response after attempting to generate lambda without `project_path` parameter by `syndicate generate lambda` command
- Remove `traceback` from response after attempting to generate lambda for non exist project by `syndicate generate lambda` command

## [0.9.0] - 2020-04-06
### Added
- Syndicate now supports configurations in YAML: syndicate.yml and syndicate_aliases.yml; The old ones (sdct.conf, sdct_alises.conf) are still supported.
- Syndicate configuration generation. Command `syndicate init --help`
- Python/Java/NodeJS project generation. Command `syndicate generate project --help`
- Python/Java/NodeJS lambda generation. Command `syndicate generate lambda --help`
- All commands from group `generate` and the command `syndicate init` are able to be executed without provided `SDCT_CONF` variable

### Changed
- All bundles now are stored to `$SDCT_CONF/bundles`folder.


## [0.8.5] - 2020-03-18
### Added
- Version option. 'syndicate --version' is now available.
- Docs for commands.
### Changed
- fixed an issue of 'The role defined for the function cannot be assumed by Lambda' while creating lambda right after the role for the lambda was created. https://github.com/epam/aws-syndicate/issues/63


## [0.8.4] - 2020-03-06
### Added
- Lambda provisioned concurrency configuration.
- LambdaProvisionedConcurrency java annotation added aws-syndicate mvn plugin.
- deployment-configuration-processor version bump to 1.5.8.
### Changed
- Lambda concurrency configuration field renamed in lambda_config.json from concurrency to max_concurrency.

## [0.8.3] - 2019-06-12
### Added
- Generation meta for Lambda Layers.

### Changed
- Lambda layer attribute renamed: fileName -> deployment_package.
- Fixed filters for resources in the 'clean' command. 

### Removed
- The 'publish_lambda_version' command. 'update' should be used instead.

## [0.8.2] - 2019-22-10
### Added
- Command 'update'. Should be used for infrastructure update instead of 'publish_lambda_version'.
- The 'replace_output' flag to 'deploy' and 'update' commands.

### Changed
- The 'publish_lambda_version' command is not recommended to use.
- Add check for existing deploy name for commands 'deploy', 'update'.
- Improved log messages.

### Removed
- No removals

## [0.8.0] - 2019-22-10
### Added
- NodeJS runtime supported.
- Implemented Lambda Layers deployment from meta.
- The 'force' flag to 'upload_bundle', 'copy_bundle', 'build_bundle' commands. 

### Changed
- Lambda layers integration while lambda creation.
- Command renamed: mvn_compile_java -> assemble_java_mvn.

### Removed
- No removals

## [0.7.0] - 2019-02-1
Initial version. See README. 
