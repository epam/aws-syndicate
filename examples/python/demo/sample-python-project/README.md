#### This example shows a Syndicate configuration for deploying:
* 3 Lambda function;
* 3 IAM role attached to lambdas;
* 3 Custom IAM policy attached to roles;
* 1 SQS queue;
* 1 DynamoDB Table
* 1 API Gateway

#### To deploy this demo project:

##### 1. Replace following placeholders in `syndicate.yml`:
* `YOUR_PATH` - actual path of the project;
* `YOUR_BUCKET_NAME` - name of AWS S3 bucket where you want syndicate to store projects artifacts;
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `ACCESS_KEY_ID` - your Secret access key acceptable of account specified in account_id;
* `SECRET_ACCESS_KEY` - your Access key ID acceptable of account specified in account_id;
* `REGION` - AWS region where syndicate will deploy this demo;

##### 2. Replace following placeholder in `syndicate_aliases.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION` - AWS region where syndicate will deploy this demo;
* `SQS_QUEUE_NAME` - Name of SQS queue that will be created;
   
##### 3. Export path to config files:
`export SDCT_CONF=$YOUR_PATH/.syndicate-config-sample-python-project`

##### 4. Create deploy target bucket
`syndicate create_deploy_target_bucket`

##### 5. Build bundle:
`syndicate build`

##### 6. Deploy
`syndicate deploy`

#### To clean demo project resources:

##### 1. Clean
`syndicate clean`