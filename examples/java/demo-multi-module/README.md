#### How to use the custom-sdk as a Lambda Layer

1. **Build the custom-sdk module:**
   - Run `mvn package` in the root or in the `custom-sdk` directory.
   - The SDK JAR will be generated at: `../custom-sdk/target/custom-sdk-1.0-SNAPSHOT.jar`

2. **Automatic placement of SDK JAR in `lib` folder:**
   - The build process is automated! When you run `mvn clean install` or `mvn package` in the root or lambda module, the SDK JAR will be automatically copied to `lambda/lib/`.
   - Example: `lambda/lib/custom-sdk-1.0-SNAPSHOT.jar` will always be up to date after a build.

3. **Lambda Layer Annotation:**
   - When using a Lambda layer annotation (e.g., for AWS Lambda Java), refer to the `lib` folder:
     ```java
     @LambdaLayer(path = "lambda/lib/")
     ```
   - This tells the build/deployment tools to include all JARs from `lib` as part of the Lambda layer.

4. **Dependency Scope:**
   - The `custom-sdk` dependency is marked as `provided` in `pom.xml` and will not be packaged in the Lambda deployment JAR. It must be present in the Lambda runtime as a layer.

#### This example shows a Syndicate configuration for deploying:
* 1 Java Lambda function with external libraries;
* 1 IAM role attached to lambda;
* 1 Custom IAM policy attached to role;
* 1 lambda function layer attached to lambda function

#### To deploy this example:

##### 1. Replace following placeholders in `syndicate.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;
* `ACCESS_KEY_ID` - Secret access key;
* `SECRET_ACCESS_KEY` - Access key ID;
* `BUCKET_NAME` - bucket name to upload deployment artifacts, must be unique across all AWS accounts;
* `PROJECT_FOLDER` - absolute path to the  project folder;

##### 2. Replace following placeholder in `syndicate_aliases.yml`:
* `ACCOUNT_ID` - AWS account id where syndicate will deploy this demo;
* `REGION_NAME` - AWS region where syndicate will deploy this demo;

##### 3. Export config files path (set environment variable SDCT_CONF):
* Unix: `export SDCT_CONF=$CONFIG_FOLDER`, in this example $CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-layer-url;
* Windows (cmd): `set SDCT_CONF=%CONFIG_FOLDER%`, in this example %CONFIG_FOLDER% is PROJECT_FOLDER/.syndicate-config-demo-layer-url;

##### 4. Build bundle:

`syndicate build`

##### 5. Deploy:

`syndicate deploy`

#### 6. To clean project resources:

`syndicate clean`

