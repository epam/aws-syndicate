#### This example shows a Syndicate configuration for deploying:
* 1 Java Lambda function;
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;
* 1 API Gateway
* 1 Cognito User Pool

#### To deploy this example:

##### 1. Replace following placeholders in `syndicate.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `BUCKET_NAME` - bucket name to upload deployment artifacts, must be unique across all AWS accounts;
* `PROJECT_FOLDER` - absolute path to the  project folder;

##### 2. Replace following placeholder in `syndicate_aliases.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `USERPOOL_NAME` - desired Cognito User Pool name;

##### 3. Export config files path (set environment variable SDCT_CONF):
* Unix: `export SDCT_CONF=$CONFIG_FOLDER`, in this example $CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-apigateway-cognito;
* Windows (cmd): `set SDCT_CONF=%CONFIG_FOLDER%`, in this example %CONFIG_FOLDER% is PROJECT_FOLDER/.syndicate-config-demo-apigateway-cognito;

##### 4. Build bundle:

`syndicate build`

##### 5. Deploy:

`syndicate deploy`

#### 6. To clean project resources:

`syndicate clean`