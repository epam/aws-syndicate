# sdct-at-ddis-aurora
The project aims to be used to test aws-syndicate secondary functionality.

## Project resources
```json
{
  "sdct-at-lambda-basic-execution-policy": {
    "resource_type": "iam_policy"
  },
  "sdct-at-java-lambda-role": {
    "resource_type": "iam_role"
  },
  "sdct-at-java-lambda": {
    "resource_type": "lambda"
  },
  "sdct-at-rds-db-cluster": {
    "resource_type": "rds_db_cluster"
  },
  "sdct-at-rds-db-instance": {
    "resource_type": "rds_db_instance"
  }
}
```

### Notice
- All resources are supposed for deployment without dependencies
- Each resource configured to be tagged with the next tags:
```json
{
  "tests": "smoke",
  "project": "sdct-auto-test"
}
```
- The AWS region where test resources will be deployed must include a default VPC and default subnet, as these are necessary for the deployment of RDS Aurora instances.
- Due to the slow deployment and cleaning of RDS resources, tests may take up to 40 minutes.
