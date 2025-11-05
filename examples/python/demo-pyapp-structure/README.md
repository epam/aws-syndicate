#### This example shows a Syndicate configuration for deploying:
* 1 Lambda function (no external libraries, no local modules);
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;

#### To deploy this example:

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

##### 3. Export path to config files:

`export SDCT_CONF={YOUR_PATH}/.syndicate-config-lambda-basic`

##### 4. Build bundle:

`syndicate build`

##### 5. Deploy:

`syndicate deploy`

##### 6. Trigger deployed lambda using aws-cli:
   `aws lambda invoke --function-name lambda_example response.json`

Response content will be stored in `response.json`:

```json
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json"
    },
    "body": "{\"Region \": \"eu-central-1\"}"
}
```

#### To clean project resources:

##### 1. Clean

`syndicate clean`

