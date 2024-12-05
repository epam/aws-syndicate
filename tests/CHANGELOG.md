## 2024-12-05
### Changed
- Changed the way to pass lambda alias to checkers - use read_sdct_conf() function from util file instead pass it with lambda name

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