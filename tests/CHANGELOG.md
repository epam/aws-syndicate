## 2025-10-13
### Added
- Added `trusted_relationships_content` checker for IAM Role trusted relationships content verification
- Fix `syndicate --version` with `--verbose` parameter

## 2025-10-07
### Added
- Added tests for `syndicate --version` command

## 2025-08-29
- Fixed an issue with building python lambda layer
- Fixed `NoSuchBucket` error during checking the existence of a Swagger UI in case the bucket does not exist

## 2025-05-06
### Added
- Added ability to specify alias in lambda env dictionary in such format: '${alias_name}'. Can be combined with wildcard
- Added tests for aurora cluster and aurora instance
- Added tests for lambda s3 trigger
### Changed
- Removed prefix, suffix and deploy_target_bucket from `init_parameters` as required parameters. 
Instead, they will be extracted from syndicate.yml config

## 2025-03-14
### Added
- Added prefixes to test project configurations and information about their usage to the readme file.
### Changed
- Changed waiting time from 5 to 10 seconds in batch_comp_env_existence_checker.

## 2025-01-21
### Added
- Added new syndicate project `sdct-at-least-used-resources` to test rare used resources, such as 
batch, step function, cloudwatch alarm, etc.
### Changed
- Renamed `sdct-auto-test` project to `sdct-at-ddis`
- Moved all configuration files to the `config` folder
- Renamed `happy_path.py` to `entry_point.py`
- Renamed `happy_path_config.json` to `ddis_resources_check_config.json`
- Changed default configuration filename to `ddis_resources_check_config.json`

## 2025-01-15
### Added
- Added appsync tests for build, deploy, update and clean commands

## 2024-12-05
### Changed
- Changed the way to pass lambda alias to checkers - use read_syndicate_aliases() function from util file instead pass it with lambda name

## 2024-11-28
### Added
- Added more logs
- Added more checks for `syndicate update` commands - tag existence, lambda environment variables, etc.
- Added ability to specify folder in deployment bucket
### Changed
- Changed the way to run `syndicate update` step - added updated versions of resource configs. More info in README
- Fixed requirements
- Fixed the bug when only the first word in the command was executed instead of the entire command in Linux OS
- Updated tags

## 2024-11-06
Initial version.
### Added
- Smoke tests which include basic checks for `syndicate build`, `syndicate deploy`, `syndicate update`, `syndicate clean` commands:
  - execution return code
  - resource existence
  - build_meta.json content
  - deployment output file content
  - bundle artifacts existence
  - resource modification (only for lambda)
  - deployment output file modification
- All resource existence checks are of the following types:
  - Lambda
  - Lambda Layer
  - IAM Policy
  - IAM Role
  - Dynamodb table
  - S3 bucket
  - API Gateway
  - SQS queue
  - SNS topic
  - Cloudwatch Rule
  - Cognito IDP
  - Swagger UI