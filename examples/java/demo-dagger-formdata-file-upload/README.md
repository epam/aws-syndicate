### This example shows a Syndicate configuration for deploying:
* 1 Java Lambda function;
  * API handler for processing API requests with multipart/formData-data content type to upload files to S3 bucket.
  * Written on Java using Dagger2 for dependency injection.
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;
  * logging permissions to write logs to CloudWatch.
  * read/write/list permissions to the S3 bucket.
* 1 API Gateway
  * API Gateway endpoint to trigger the lambda function.
  * enabled proxy to forward requests to the lambda function.
  * CORS enabled to allow requests from any origin.
  * binary media types configured to support multipart/form-data content type.


### To deploy this example:

#### 1. Replace following placeholders in `syndicate.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `BUCKET_NAME` - bucket name to upload deployment artifacts, must be unique across all AWS accounts;
* `PROJECT_FOLDER` - absolute path to the  project folder;

#### 2. Replace following placeholder in `syndicate_aliases.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `STORAGE_BUCKET_NAME` - name of existing, already deployed S3 bucket used for file storage;

#### 3. Export config files path (set environment variable SDCT_CONF):
* Unix: `export SDCT_CONF=$CONFIG_FOLDER`, in this example $CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-dagger-formdata-file-upload;
* Windows (cmd): `set SDCT_CONF=%CONFIG_FOLDER%`, in this example %CONFIG_FOLDER% is PROJECT_FOLDER/.syndicate-config-demo-dagger-formdata-file-upload;

#### 4. Build bundle:

`syndicate build`

#### 5. Deploy:

`syndicate deploy`

#### 6. To clean project resources:

`syndicate clean`

### To check functionality:

#### 1. Create a new S3 bucket or choose an existing one to use as storage for uploaded files.

#### 2. Deploy the project using the steps above.

#### 3. Sign in the AWS Console, go to the Lambda > Configurations > Triggers and copy the API endpoint: 
* Example: 'https://19optwbq61.execute-api.ap-southeast-1.amazonaws.com/api/files'

#### 4. Open in browser simple HTML page `index.html` from the `PROJECT_FOLDER/frontend` folder, fill the input fields `URL:` with the obtained API endpoint both in the `GET Request` and `POST Request` areas

#### 5. In the `POST request` area, fill in the `User Name:` and `Description:` text input fields, select some lightweight files using the `Choose Files` selector, and submit the POST request by clicking the `Send POST` button.

#### 6. The response will be displayed in the `Response` area and contains urls of uploaded files that stored in the S3 bucket.
* These URLs can be used to download files if access to the S3 bucket contents is configured to allow.
