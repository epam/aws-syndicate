# sdct-at-secondary-project
The project aims to be used to test aws-syndicate secondary functionality.

## Project resources
```json
{
  "sdct-at-batch-job-role": {
    "resource_type": "iam_role"
  },
  "sdct-at-compenv": {
    "resource_type": "batch_compenv"
  },
  "sdct-at-job-queue": {
    "resource_type": "batch_jobqueue"
  },
  "sdct-at-job-definition": {
    "resource_type": "batch_jobdef"
  }
}
```

### Notice
- The next resources are supposed for deployment without dependencies:
```json
{
  "sdct-at-batch-job-role": {
    "resource_type": "iam_role"
  },
  "sdct-at-compenv": {
    "resource_type": "batch_compenv"
  },
  "sdct-at-job-queue": {
    "resource_type": "batch_jobqueue"
  },
  "sdct-at-job-definition": {
    "resource_type": "batch_jobdef"
  }
}
```
- Each resource configured to be tagged with the next tags:
```json
{
  "tests": "smoke",
  "project": "sdct-auto-test"
}
```
## Subnet and Security Group dependency
To deploy a Batch Compute Environment, you need to specify **ANY** subnet and security group so that there are no 
errors when executing build and deploy commands. The security group and subnet IDs should be specified in the 
syndicate_aliases.yml file in the following form:
```yml
sg_id: sg-ID
subnet_id: subnet-ID
```