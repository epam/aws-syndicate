#### This example shows a Syndicate configuration for deploying:
* 1 Lambda function (1 external library, 1 local module);
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;

#### To deploy this example:

##### 1. Replace following placeholders in `sdct.conf`:
* `YOUR_PATH` - actual path of the project;
* `YOUR_BUCKET_NAME` - name of AWS S3 bucket where you want syndicate to store projects artifacts;
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `ACCESS_KEY_ID` - your Secret access key acceptable of account specified in account_id;
* `SECRET_ACCESS_KEY` - your Access key ID acceptable of account specified in account_id;

##### 2. Replace following placeholder in `sdct_aliases.conf`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;

##### 3. Export path to config files:
`export SDCT_CONF={YOUR_PATH}/aws-syndicate/examples/python/lambda-external-libraries`

##### 4. Build bundle:
`syndicate build_bundle --bundle_name example`

##### 5. Deploy:
`syndicate deploy --bundle_name example --deploy_name example`


##### 6. Trigger deployed lambda using aws-cli:
`aws lambda invoke --function-name lambda_example --payload '{"url": "https://api.github.com/"}' --cli-binary-format raw-in-base64-out response.json`

Response content will be stored in `response.json`:
```json
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json"
    },
    "body": "{\"url\": \"https://api.github.com/\", \"status_code\": 200, \"response_time\": \"0.112317s.\"}"
}
```

##### 7. Clean:
`syndicate clean --bundle_name example --deploy_name example`

