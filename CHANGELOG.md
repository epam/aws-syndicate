# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [1.3.2] - 2023-09-20
- Fixed ignored request parameters when creating api gateway's resource method using lambda integration

# [1.3.1] - 2023-09-20
- Add support Python 3.10 and Python 3.11

# [1.3.0] - 2023-09-14
- Added ability to use SSO credentials
- Added parameter `aws_session_token` to `sdct.conf` for role assuming

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
