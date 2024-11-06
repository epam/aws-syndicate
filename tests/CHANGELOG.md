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