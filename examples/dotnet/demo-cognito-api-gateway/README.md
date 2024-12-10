# demo-cognito-api-gateway

This is a demo aws-syndicate project that shows the usage API Gateway, Lambda function, and Cognito User Pool in one solution

## Lambdas descriptions

### Lambda `api_handler`
Lambda overview.

### Required configuration
In the project, the Cognito User Pool ID and Cognito User Pool client ID are utilized. To access these values in the lambda code, the environment variables cup_id and cup_client_id have been configured. During deployment, aws-syndicate will resolve the actual values and assign them to the appropriate variables. It is important to note the need to include the Cognito User Pool in the lambda dependencies.

All the configurations mentioned are set up in the lambda_config.json file.

#### Environment variables
* cup_id: Cognito User Pool ID will be here
* cup_client_id: Cognito User Pool client ID will be here



