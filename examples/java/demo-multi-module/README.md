## Example: Multi-Module AWS Lambda Project with Custom SDK via Lambda Layer

This is an example of a **multi-module Maven project** for AWS Lambda. It demonstrates how to structure and deploy a Java Lambda function using a **custom SDK module** that is delivered via a **Lambda Layer**, not bundled into the main Lambda deployment JAR.

### Project Structure

The project is split into two Maven modules:

1. **`custom-sdk`**
   Contains reusable Java code (SDK) that is **not included in the Lambda JAR**, but instead provided via a Lambda Layer at runtime.

2. **`lambda`**
   Contains the actual Lambda function code. It depends on the `custom-sdk` module but marks it as `provided` to exclude it from the build artifact. The Lambda function accesses the SDK classes via the Lambda Layer.

## How the Setup Works

* The Lambda function **depends on** the `custom-sdk`, but the dependency is declared with `scope: provided`, meaning it **won't be packaged** in the Lambda JAR.
* Instead, the `custom-sdk` is built into a separate JAR and **included in a Lambda Layer**, which is then **attached to the Lambda function**.
* This design keeps the Lambda deployment package smaller and modular.

## How to Use the Custom SDK as a Lambda Layer

### 1. Build the `custom-sdk` Module

Run the following command in the root project or inside the `custom-sdk` folder:

```bash
mvn package
```

After build, the SDK JAR will be available at:

```
custom-sdk/target/custom-sdk-1.0-SNAPSHOT.jar
```

---

### 2. Automatic Placement of SDK JAR in `lib/` Folder

When you run:

```bash
mvn clean install
```

or

```bash
mvn package
```

…the `custom-sdk` JAR is **automatically copied** to the Lambda module's `lib/` folder:

```
lambda/lib/custom-sdk-1.0-SNAPSHOT.jar
```

This ensures the Lambda Layer always includes the latest SDK version.

### 3. Lambda Layer Annotation in Code

In your Lambda code, you can use the `@LambdaLayer` annotation to indicate where the Layer libraries are:

```java
@LambdaLayer(
   layerName = "my-custom-libs",
   description = "Custom libraries layer",
   libraries = {"lambda/lib/custom-sdk.jar"},
   runtime = DeploymentRuntime.JAVA17,
   architectures = {Architecture.X86_64}
)
```

This tells the build/deployment tools to package everything in the `lib/` folder as part of the Lambda Layer.

### 4. `custom-sdk` Dependency Scope

Make sure the SDK is added as a `provided` dependency in `lambda/pom.xml`:

```xml
<dependency>
  <groupId>com.example</groupId>
  <artifactId>custom-sdk</artifactId>
  <version>1.0-SNAPSHOT</version>
  <scope>provided</scope>
</dependency>
```

This excludes it from the final Lambda deployment JAR.

## Deployment with Syndicate

This example is configured to use **[Syndicate](https://github.com/epam/aws-syndicate)** for deployment. It deploys:

* 1 Java Lambda function using external libraries via Layer
* 1 IAM role for the Lambda function
* 1 custom IAM policy attached to the role
* 1 Lambda Layer with `custom-sdk`
* All via simple configuration and commands.

### Deployment Steps

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