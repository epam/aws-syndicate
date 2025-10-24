# sdct-at-ddis
The project aims to be used to test aws-syndicate main functionality which is used by students in the 
"Deep Dive into Serverless" course.

## Project resources
```json
{
    "sdct-at-lambda-basic-execution-policy": {
      "resource_type": "iam_policy"
    },
    "sdct-at-java-lambda-role": {
      "resource_type": "iam_role"
    }, 
    "sdct-at-appsync-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-java-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-java-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-dotnet-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-dotnet-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-dotnet-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-python-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-python-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-python-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-queue": {
      "resource_type": "sqs_queue"
    },
    "sdct-at-topic": {
      "resource_type": "sns_topic"
    },
    "sdct-at-table": {
      "resource_type": "dynamodb_table"
    },
    "sdct-at-reservation": {
      "resource_type": "dynamodb_table"
    },
    "sdct-at-cw-rule": {
      "resource_type": "cloudwatch_rule"
    },
    "sdct-at-s3-bucket": {
      "resource_type": "s3_bucket"
    },
    "sdct-at-swagger-ui": {
      "resource_type": "swagger_ui"
    },
    "sdct-at-nodejs-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-nodejs-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-nodejs-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "${booking_userpool}": {
      "resource_type": "cognito_idp"
    },
    "sdct-at-api-gw": {
      "resource_type": "api_gateway"
    },
    "sdct-at-open-api-gw": {
      "resource_type": "api_gateway_oas_v3"
    },
    "sdct-at-appsync": {
      "resource_type": "appsync"
    }
}
```

### Notice
- The project contains at least one resource of each type used in the course Deep Dive into Serverless
- In case of deployment of all the project resources, they will be deployed with dependencies
- The next resources are supposed for deployment without dependencies:
```json
{
    "sdct-at-lambda-basic-execution-policy": {
      "resource_type": "iam_policy"
    },
    "sdct-at-java-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-appsync-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-java-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-java-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-dotnet-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-dotnet-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-dotnet-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-python-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-python-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-python-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-queue": {
      "resource_type": "sqs_queue"
    },
    "sdct-at-topic": {
      "resource_type": "sns_topic"
    },
    "sdct-at-table": {
      "resource_type": "dynamodb_table"
    },
    "sdct-at-reservation": {
      "resource_type": "dynamodb_table"
    },
    "sdct-at-cw-rule": {
      "resource_type": "cloudwatch_rule"
    },
    "sdct-at-s3-bucket": {
      "resource_type": "s3_bucket"
    },
    "sdct-at-swagger-ui": {
      "resource_type": "swagger_ui"
    },
    "sdct-at-appsync": {
      "resource_type": "appsync"
    }
}
```
- The next resources are supposed for deployment with dependencies:
```json
{
    "sdct-at-nodejs-lambda-role": {
      "resource_type": "iam_role"
    },
    "sdct-at-nodejs-lambda": {
      "resource_type": "lambda"
    },
    "sdct-at-nodejs-lambda_layer": {
      "resource_type": "lambda_layer"
    },
    "sdct-at-cup": {
      "resource_type": "cognito_idp"
    },
    "sdct-at-api-gw": {
      "resource_type": "api_gateway"
    },
    "sdct-at-open-api-gw": {
      "resource_type": "api_gateway_oas_v3"
    }
}
```
- Each resource except swagger_ui configured to be tagged with the next tags:
```json
{
  "tests": "smoke",
  "project": "sdct-auto-test"
}
```

## Lambdas descriptions

### Lambda `sdct-at-nodejs-lambda`
#### depends on:
  - sdct-at-cup
#### linked layers:
  - sdct-at-nodejs-lambda_layer
#### env variables:
  - cup_id
  - cup_client_id

### Lambda `sdct-at-dotnet-lambda`
#### linked layers:
  - sdct-at-dotnet-lambda_layer
#### env variables:
  - DOTNET_SHARED_STORE
#### event sources:
  - sdct-at-topic

### Lambda `sdct-at-java-lambda`
#### linked layers:
  - sdct-at-java-lambda_layer
#### event sources:
  - sdct-at-cw-rule

### Lambda `sdct-at-python-lambda`
#### linked layers:
  - sdct-at-python-lambda_layer
#### event sources:
  - sdct-at-queue

