# demo-apigateway-cognito

A small Syndicate example that deploys:
- A Java Lambda function
- An IAM role and custom policy for the Lambda
- An API Gateway fronting the Lambda
- A Cognito User Pool

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Build & Deploy](#build--deploy)
- [Cleanup](#cleanup)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)
``
---

## Prerequisites

- Syndicate CLI installed and available on PATH
- AWS credentials configured (via environment or aws cli)
- A unique S3 bucket for storing deployment artifacts


## Configuration

1. Update syndicate.yml placeholders:
   - `ACCOUNT_ID` — AWS account ID that will host the demo
   - `REGION_NAME` — AWS region for deployment
   - `BUCKET_NAME` — S3 bucket for artifacts (must be globally unique)
   - `PROJECT_FOLDER` — absolute path to the project folder

2. Update syndicate_aliases.yml placeholders:
   - `ACCOUNT_ID` — same AWS account
   - `REGION_NAME` — same AWS region
   - `USERPOOL_NAME` — desired Cognito User Pool name

3. Export configuration folder via SDCT_CONF:

- Unix / macOS (bash/zsh):

```bash
export SDCT_CONF=$CONFIG_FOLDER
# where CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-apigateway-cognito
```

- Windows (cmd):

```cmd
set SDCT_CONF=%CONFIG_FOLDER%
REM where CONFIG_FOLDER is PROJECT_FOLDER/.syndicate-config-demo-apigateway-cognito
```

- Windows (PowerShell):

Temporary (current PowerShell session):

```powershell
$env:SDCT_CONF = $env:CONFIG_FOLDER
# or: $env:SDCT_CONF = 'C:\path\to\PROJECT_FOLDER\.syndicate-config-demo-apigateway-cognito'
```

Persistent (across sessions):

```powershell
setx SDCT_CONF "$env:CONFIG_FOLDER"
# or: setx SDCT_CONF "C:\path\to\PROJECT_FOLDER\.syndicate-config-demo-apigateway-cognito"
```

> Tip: Use the provided example config directory under the project to speed setup.

## Build & Deploy

From the project root (or where syndicate.yml is reachable):

```bash
syndicate build
syndicate deploy
```

After deploy the API Gateway and Cognito resources will be provisioned as defined in the config.

## Cleanup

To remove the resources created by this example:

```bash
syndicate clean
```

## Notes

- Replace placeholders carefully—ACCOUNT_ID and BUCKET_NAME are critical for successful deployment.
- The PROJECT_FOLDER should point to the example project root so Syndicate can find sources and artifacts.

## Contributing

Contributions, fixes and improvements are welcome. Please open issues or pull requests against the main repository: https://github.com/epam/aws-syndicate

## License

See the repository LICENSE file for licensing information.
