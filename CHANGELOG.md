# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [1.17.1] - 2025-03-07
- Changed `--force_upload` parameter type for assemble commands from `string` to `flag`
- Fixed logic of `--force_upload` flag in assemble commands
- Added `--force_upload` flag to `assemble_appsync` and `assemble_swagger_ui` commands

# [1.17.0] - 2025-03-03
- Added the possibility to generate meta for the resources `firehose` and `eventbridge_schedule`
- The operation `partial_clean` added to the modification operations list
- Fix typos in commands help messages
- Sort available commands in help output alphabetically
- Adjust EventBridge Scheduler target meta to snake_case
- Fix an issue where a lambda would not bind to a CloudWatch alarm if the lambda had not been created previously
- Improved errors logging
- Added the verification of MVN installation before assembling Java artifacts
- Added highlighting messages with colors in the user console log according to the level
- Fixed log message duplication during retries
- Fixed issue related to deployment API Gateway defined with OpenAPI spec and documented path `Path Item Object` 
- Added syndicate custom exceptions
- Clarified warning message about the absence of the syndicate project state file.
- Added lambda function `event_sources` validation on the build stage.
- Added verification whether the resource was cleaned in case of errors during clean operation.
- Fixed `lambda_layer` duplication during deployment.
- Fixed an issue related to deploy target bucket creation

# [1.16.2] - 2025-01-24
- Fixed an issue related to modification operations event synchronization

# [1.16.1] - 2025-01-21
- Added sync project state to the project state initialization
- Fixed an issue related to `build_project_mapping` resolving for `appsync`, `swagger_ui`, and `lambda` functions with runtime .NET  resources
- Separated parameters required to execute maven commands for Windows and for other operating systems

# [1.16.0] - 2025-01-14
- Added support for the AppSync resource
- Added the possibility to generate `s3_bucket` meta for static website hosting without public access
- Added the possibility to manage CloudWatch logging for API Gateway resources
- Added an example of lambda function URL configuration to the Python example 'lambda-basic'
- Improve the assembling of the Java lambda artifacts by removing the redundant original-<lambda_name>.jar file from the bundle
- Improved `modification_lock` resolving to avoid conflicts in case of work a few users with the same project
- Improved logging during generation lambda functions and lambda layers
- Improved user message in case the bundle name was not resolved
- Improved output of the command `status`
- Improved logging during building .NET artifacts
- Standardized console user messages
- Added error summary to console log in case of unexpected error occurrence
- Added parameter `--errors_allowed` to the command `assemble_java_mvn`
- Update `zip_dir` to handle cases where the full path length exceeds 260 characters with a more informative error message
- Ensure `zip_dir` validates the existence of the base directory before proceeding with the zipping process
- Unify manage resources via create_pool (+ DynamoDB tables and CloudWatch alarms)
- Fixed events registering to the state file(.syndicate) in case of internal errors
- Fixed an issue related to generating the lambda function with runtime Java when the project root file deployment_resources.json is absent
- Fixed issue related to building a project that contains no lambda functions
- Fixed duplication lambda function and lambda layer records in the output file after updating the resources
- Fixed issue related to lambda function updating in case of changing lambda's alias name
- Fixed issue related to tests generation for lambda function with runtime Python
- Fixed duplication of the API Gateway of type `web_socket_api_gateway` during deployment
- Fix `tag_resources` and `untag_resources` to handle exceptions properly
- Update `apply_tags`, `remove_tags`, and `update_tags` to return success status
- Fix `clean` command for `output` folder to correctly resolve ARN for Lambda and properly process and remove the `outputs` folder if Lambda is part of the deployment
- Fix bucket name resolver to raise a user-friendly message if the bucket name does not match the specified regex
- Fix `deploy` for `ec2 launch template` with tags
- Add resource tags for `ec2 launch-template` and  for versions in update and deploy operations
- Add support tags for `OAS V3` as part of the `oas_v3.json` file, using the `x-syndicate-openapi-tags` key
- Remove the directory 'target' that contains temporary files after assembling lambda artifacts
- Unused library `colorama` removed from the requirements
- Correct the return code of all the commands if they failed or were aborted
- Java plugin version updated to 1.15.0 with changes:
  - Added the verification of Lambda resources existence to prevent deploy without Lambda resources
  - Added support of the syndicate `--errors_allowed` flag to skip build process interruption in case of errors
- Java template updated to use the Syndicate Java plugin version 1.15.0 for the new lambda generation
- Java examples updated to use the Syndicate Java plugin version 1.15.0
- Fix bug when assembling multiple lambdas with different runtimes with `--force_bundle` flag

# [1.15.0] - 2024-10-28
- Added `--skip_tests` option to `build`, `test` and `assemble_java_mvn` commands to not run tests during or after 
building the bundle
- Added `--errors_allowed` option to `assemble_python` and `assemble` commands
- Improved logic of option `--errors_allowed` to allow dependency installing if it is not possible to find a 
requirement that fits a specific platform. In this case, the dependencies will be installed independently 
of each other or without specifying a specific platform (using default platform `any`). Python-specific feature
- Fixed updating lambda layers when the lambda no longer has layers
- Fixed logging not found exceptions during the clean operation
- Fixed handling of deployment output in case of failures on the stage describe resources in case of deploy/update fail
- Implemented handling of failures during the clean action
- Improved error message if errors occur during Python requirements installation
- Changed log level from info to warn if updating of the resource skipped because of absence in the deployment output
- Fixed deploying a new bundle if latest deploy output is missing
- Fixed a bug when the latest deployment section was updated when the `deploy` command ended with the ABORTED status
- Fixed an issue related to locking the state
- Added empty deployment package handling for lambda layer
- Fixed bug when meta output processor process the resource name incorrectly
- Fix `clean` command for `output` folder to correctly resolve ARN for Lambda and properly process and remove the `outputs` folder if Lambda is part of the deployment

# [1.14.1] - 2024-10-08
- Added support lambda layers with runtime DotNet
- Tagging added to `oas_v3 openapi` API Gateway.
- SNS topic deletion fixed.
- Added an example of a lambda function with runtime `dotnet`
- Fixed silent overwriting existing lambda with runtime Java during the command `syndicate generate lambda`

# [1.14.0] - 2024-08-28
- Changed deployment flow to work despite the latest deployment failed
- Changed deployment flow with the flag `--continue_deploy` to work despite the latest deployment being absent or succeeded
- Implemented rolling back on error mechanism(flag `--rollback_on_error`) for deployment flow with the flag `--continue_deploy`
- Added support of lambda functions with runtime DotNet
- Added possibility to deploy/update resource-specific tags
- Added confirmation request mechanism for the `update` command in case the latest deployment failed
- Added the flag `--force` for the `update` command to run an update without confirmation request in case the latest deployment failed
- Added proper messages for commands `update` and `clean` if deployed resources are absent(output file not found)
- Added logging of resource names that cause errors to improve error diagnostics
- Added enhanced logging of the `build` command execution
- Added validation for existence of bundle and deploy names
- Added validation for incompatible parameters(`--events`, `--resources`) of the command `syndicate status`
- Added the possibility to add resource-specific tags via the resource meta generation(flag `--tags`)
- Added tags support to the Syndicate Java plugin. The `@Tags` and the `@Tag` annotations added to the plugin. The Java plugin version updated to 1.14.0
- Changed the Java lambda template to use the Syndicate Java plugin version 1.14.0 for the new lambda generation.
- Event status added to the command `syndicate status` output
- Reworked lambda triggers update to compare local event sources meta with the previous remote one
- Reworked lambda triggers deletion to not list every resource of the trigger type to remove it from lambda (**EPMCEOOS-6112**)
- The key `operation_status` in `latest_deploy` section of the syndicate state file(.syndicate) renamed to `is_succeeded`
- Fixed lock resolving issue
- Fixed an issue related to bucket name resolving in the s3_bucket policy
- Added logging of resource names that cause errors to improve error diagnostics
- Fix the resource update issue that occurs when a deploy_name is specified by user (not default one) but deployment 
output for the latest deployment is empty
- Fixed an issue where updating only certain resources caused the deployment output to be overwritten with only these 
resources, instead of updating the existing meta
- Fixed deployment failure if resource name is the same as resource type
- Fixed an issue related to resource name resolving if ARN is a list item
- Fixed an issue related to name resolving if one resource name contains another resource name
- Fixed an issue when a lambda deployment fails when a trigger defined in meta does not exist
- Fixed an issue related to updating lambda triggers
- Fixed lambda event source mapping inactivity after deployment
- Improved logging for the deletion of a resource that does not exist in the account
- Improved logging in case of the absence of resources to clean
- Fixed Lambda Layer packaging for the NodeJS runtime
- Fixed an issue where newly added resources (after deploy) were causing the update operation to fail
- Fixed a synchronization issue that prevented the batch job queue from being deleted before its state was fully updated
- Fixed an issue related to removing CloudWatch alarms that were used for Dynamodb autoscaling
- Fixed an issue with the absence of lambda's information in the output file in case deployment failed on the trigger configuration step
- Fixed an issue related to losing state after partial clean
- Fixed an issue related to the latest output resolving
- Fixed an issue related to the API Gateway throttling and cache configuration for ANY method
- Fixed an issue with `--force_upload` being required while syndicate assemble

# [1.13.1] - 2024-08-05
- Speed up deletion of s3 bucket with lots of objects

# [1.13.0] - 2024-07-10
- Added possibility to configure `FunctionResponseTypes` for lambda functions
- Updated maven plugin version to 1.12.0 with support of `FunctionResponseTypes`
- Added possibility to set up Cognito user pool ID in lambda function environment variable
- Added possibility to set up Cognito user pool client ID in lambda function environment variable
- Fix lambda triggers deletion when removed from meta
- Fix resources dependencies resolving
- Fix losing successfully deployed resources from the output file during deployment with the option `--continue_deploy`
- Fix API Gateway duplication in case of existing API Gateway with the same name
- Fix detection of usage `--rollback_on_error` option with an incompatible option `--continue_deploy`
- Changed datetime format for lock attributes in the `.syndicate` file to UTC format
- The Syndicate Java plugin version updated to 1.13.0 with changes:
  - The ResourceType enum for the @DependsOn annotation extended with new type ResourceType.COGNITO_USER_POOL
  - The @EnvironmentVariable annotation for the Syndicate Java plugin improved to support the value transformer
  - A new value transformer type created ValueTransformer.USER_POOL_NAME_TO_USER_POOL_ID
  - A new value transformer type created ValueTransformer.USER_POOL_NAME_TO_CLIENT_ID
- The generate Java lambda template changed to use the Syndicate Java plugin version 1.13.0

# [1.12.0] - 2024-06-20
- Added ability for `clean` command to automatically resolve if `--rollback` is needed.
- Fixed an issue related to `log group already exists` error while deploying or updating `lambda`.
- Updated `syndicate deploy --continue_deploy` command, now it can save output and actually continue deployment resources.
- Implemented `rollback_on_error` flag for `syndicate deploy` command. Is flag is `True`, all resources that have been deployed during deployment process, would be cleaned.
- Fixed an issue related to deploying multiple resources with same type, now it catches an `Exception` in case of a deployment error of one of the resources and returns it along with the outputs.
- Fixed `deploy` command responses.
- Added support of Python 3.12
- Fixed an issue related to ARNs resolving in case of empty resource name
- Fixed an issue related to improper filtering of resources in case of different types of filter usage
- Fixed an error related to SQS FIFO Queue availability regions
- Fixed an issue related to deploying SQS Queue with configured redrive_policy
- Fixed an issue when only the last s3 trigger was configured for the lambda
- Added `force_upload` action to all assemble commands

# [1.11.6] - 2024-05-24
- Added support of custom authorizer names in Open API specification security schemes
- Fixed quietness of errors while deploying/updating API Gateway via OpenAPI specification
- Fixed API GW deletion when openapi specification is invalid
- Fixed issue with the command `generate meta api_gateway_resource`
- Fixed lambda function deployment fails in case of matching any resource name with prefix or/and suffix

# [1.11.5] - 2024-05-09
- Syndicate Java plugin patched to version 1.11.1 to exclude extra dependencies
- Fixed an error related to export OpenAPI specification in extended prefix mode

# [1.11.4] - 2024-04-30
- Added support of EC2 Launch Templates(`ec2_launch_template`)
- Change log level (for non-last exceptions) in retry decorator from error to warning
- add `.syndicate-config-*/` to generated project gitignore
- Fixed an error in case of an attempt to delete a nonexistent API Gateway
- Add error log in case of invalid resource type
- Fixed an error in case of an attempt to delete a nonexistent IAM Policy
- Fixed an error in case of an attempt to delete a nonexistent SNS Topic
- Fixed an error related to `UpdateEventSourceMapping operation` during SQS trigger deployment

# [1.11.3] - 2024-04-16
- Added support of Python 3.12 lambda runtime
- Root account removed from trusted entities of autogenerated lambda’s role
- Improve bundle name validation: exclude folder path from length validation
- - Added an ability to build lambdas and lambda layers with local requirements (for `nodejs` runtime)
- Implemented subnet group deletion with deletion of the related DAX if the syndicate deployed it
- Fixed deploy target bucket key compound appending to artifact src in swagger ui resource
- Clarified the error message when copying NodeJS dependencies folder
- Changed the error log message to the warning when updating log group retention period
- Made a bunch of changes to the CloudWatch Alarm resource:
  * added the ability to add ALARM actions for Lambdas and System Manager (incident manager); 
  * added new parameters to the resource description in the deployment_resources: `description`, `datapoints`, `dimensions` and `evaluate_low_sample_count_percentile`;
  * added new parameters to the `syndicate generate meta cloudwatch_alarm` command: `description`, `datapoints` and `evaluate_low_sample_count_percentile`; 
  * added more values to the `comparison_operator` parameter: `LessThanLowerOrGreaterThanUpperThreshold`, `LessThanLowerThreshold`, `GreaterThanUpperThreshold`
- Fixed bug when lambda invocation permissions in lambda`s alias were not removed after the web_socket_api_gateway was destroyed
- Fixed displaying help messages with partially specified credentials
- Added more error logs in retry function which assumes aws credentials
- Added verbose mode (flag `--verbose|-v`)
- improved project lock logic to make it configurable and time-limited

# [1.11.2] - 2024-03-28
- Fix issue with syndicate not uploading deploy output on fail

# [1.11.1] - 2024-03-26
- Added clarification error message in case of deployment after failed deploy
- Fixed generation of tests when generating meta for a new lambda function
- Fixed a deployment error when `sqs|stream` lambda trigger `batch_size` value is greater than 10
- Fixed an error in case of an attempt to tag a resource of type `swagger_ui`
- Removed redundant dependencies from the Java plugin

# [1.11.0] - 2024-03-15
- Added new resource type `swagger_ui`
- Added support of Eventbridge rule
- Added generation of lambda layer meta, the command `syndicate generate lambda_layer`
- Added an ability to build and deploy lambda layers with `nodejs` runtime
- Added lambda function processor architecture type management
- Added lambda layers compatible processor architecture types management
- The @LambdaHandler annotation for Java plugin improved to support the lambda 'architecture' management
- The @LambdaLayer annotation for Java plugin improved to support the lambda 'architectures' management
- Added meta generation for  API gateway authorizer
- Added `api_source_arn` when creating permission for lambda authorizer.
- Added API Gateway `Throttling` settings management
- Added the feature "export api gateway OpenAPI spec"
- Added support for OpenAPI v3 deploy, update and clean-up in API Gateway
- Added lambda functions resource-based policy adjustment when integration with API Gateway defined with OpenAPI v3 spec
- Added Cognito User Pools ARNs resolving for OpenAPI specification via the key `x-syndicate-cognito-userpool-names` of the `x-amazon-apigateway-authorizer` extension
- Added S3 bucket deployment with configuration for static website hosting
- Added CloudWatch logs expiration management
- Added validation for the configuration parameter `iam_suffix`
- Added warning to logs in case of unknown parameters in the configuration file
- Added the parameter `--preserve_state` to the `syndicate clean` command to keep the deployment output file
- Added validation of composite deploy_target_bucket (bucket_name+prefix) to the command `syndicate generate config`
- Added ability to generate syndicate configs with temporary set of credentials
- Improved the Lambda SQS Trigger Creation process to check for existing event
source mapping, and update or create if needed.
- Change in `syndicate generate config` command default value for `lambdas_alias_name`
from `prod` to `dev`
- Fixed inconsistency of the project state in case of several deployments
- Fixed skipping deploy|update|clean resources with filtering by name when prefix and/or suffix specified in syndicate configuration
- Fixed a bug when an empty requirements.txt file with a newline would cause the project to fail to build
- Fixed API Gateway deployment with the default value(300) of the `Cache time to live` parameter if the specified value is `0`
- Fixed lambda authorization permissions
- Fixed AWS Batch Compute environment deployment issue in case of specifying the parameter `--allocation_strategy`
- Fixed DAX cluster deployment error when DAX Role is deploying on the fly
- Fixed Dax cluster meta generation error in case of specifying subnet group name and subnets IDs
- Fixed the help message for the parameter `--security_group_names` of the command `syndicate generate meta ec2_instance`
- Fixed a mechanism of linking API gateway resource methods with an authorizer
- Fixed an issue related to clean resources after a partial clean
- Fixed displaying help messages without configured SDCT_CONF environment variable
- Upgraded default Java Lambada runtime from Java 8 to Java 11
- Added support of Lambda runtime Java 17 and Java 21
- Upgraded default NodeJS lambda runtime version from 14.x to 20.x
- Updated available NodeJS lambda runtime versions from 10.x/12.x/14.x to 16.x/18.x/20.x
- Actualized Java project examples
- Actualized Python project examples
- Removed obsolete documentation (/docs)

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
