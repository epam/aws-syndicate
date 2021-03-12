#### This example shows a Syndicate configuration for deploying:
* 1 Lambda function;
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;
* 1 DynamoDB Table
* 1 API Gateway

#### To deploy this example:

##### 1. Replace following placeholders in `sdct.conf`:
* `YOUR_PATH` - actual path of the project;
* `YOUR_BUCKET_NAME` - name of AWS S3 bucket where you want syndicate to store projects artifacts;
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `ACCESS_KEY_ID` - your Secret access key acceptable of account specified in account_id;
* `SECRET_ACCESS_KEY` - your Access key ID acceptable of account specified in account_id;

##### 2. Replace following placeholder in `sdct_aliases.conf`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION` - AWS region where syndicate will deploy this demo;

##### 3. Export path to config files:
`export SDCT_CONF=$YOUR_PATH/aws-syndicate/examples/python/lambda-dymano-api-gateway`

##### 4. Build bundle:
`syndicate build_bundle --bundle_name example`

##### 5. Deploy:
`syndicate deploy --bundle_name example --deploy_name example`

##### 6. Check api was created:
`aws apigateway get-rest-apis`

Response must contain just created `syndicate-demo-api`:

```json
{
   "items": [
      {
         "id": "bzztcmtw94",
         "name": "syndicate-demo-api",
         "createdDate": "2021-03-11T10:59:33+02:00",
         "apiKeySource": "HEADER",
         "endpointConfiguration": {
            "types": [
               "EDGE"
            ]
         },
         "disableExecuteApiEndpoint": false
      }
   ]
}
```
##### 7. Check DynamoDB table was created:
   
`aws dynamodb list-tables`

Response must contain just created `Notifications` table:
```json
{
    "TableNames": [
        "Notifications"
    ]
}

```
##### 8. Trigger deployed lambda using aws-cli:
   
`aws lambda invoke --function-name put_dynamodb_item --payload '{"id": "10", "event": "some event"}' --cli-binary-format raw-in-base64-out response.json`

Response content will be stored in `response.json`:

```json
{
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json"
    },
    "body": "{...}"
}
```

##### 9. Clean:
`syndicate clean --bundle_name example --deploy_name example`

