#### This example shows a Syndicate configuration for deploying:
* 1 Java Lambda function;
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;
* 1 DynamoDb table
* 1 S3 bucket

#### To deploy this example:

##### 1. Replace following placeholders in `syndicate.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `ACCESS_KEY_ID` - Secret access key;
* `SECRET_ACCESS_KEY` - Access key ID;
* `BUCKET_NAME` - bucket name to upload deployment artifacts, must be unique across all AWS accounts;
* `PROJECT_FOLDER` - absolute path to this project folder;

##### 2. Replace following placeholder in `syndicate_aliases.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `NOTIFICATION_BUCKET` - name of AWS S3 bucket where lambda will store notifications;

##### 3. Export config files path (set environment variable SDCT_CONF):
* Unix: `export SDCT_CONF=$CONFIG_FOLDER`, in this example $CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-java;
* Windows (cmd): `set SDCT_CONF=%CONFIG_FOLDER%`, in this example %CONFIG_FOLDER% is PROJECT_FOLDER/.syndicate-config-demo-java;

##### 4. Build bundle:

`syndicate build`

##### 5. Deploy:

`syndicate deploy`

#### 6. To clean project resources:

`syndicate clean`