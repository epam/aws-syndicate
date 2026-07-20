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

## API Documentation

### OpenAPI Specification

The full API contract — including the intentional Cognito authorizer token
validation behavior demonstrated by this example — is documented in
[`docs/open-api.yaml`](./docs/open-api.yaml).

> **Why this matters:** this API intentionally exposes endpoints secured with
> both an **ID Token** and an **Access Token** to demonstrate a well-known but
> often misunderstood Cognito + API Gateway behavior: whether the built-in
> Cognito authorizer validates the incoming bearer token as an ID Token or an
> Access Token depends entirely on whether `authorizationScopes` is configured
> on the method. See the `info.description` section of the OpenAPI spec for
> the full explanation, including which token type causes `401 Unauthorized`
> on which endpoint and why.

You can preview/explore the spec using any OpenAPI-compatible tool, e.g.:

```bash
npx @redocly/cli preview-docs docs/open-api.yaml
```

## Postman Collection

A ready-to-use Postman collection is provided at
[`docs/postman/demo-apigateway-cognito.postman_collection.json`](./docs/postman/demo-apigateway-cognito.postman_collection.json),
covering:

- `sign-up`, `sign-in`, `refresh-token`, `sign-out`
- The unsecured endpoint
- The ID-Token-secured endpoint (antipattern demo)
- The Access-Token-secured endpoint (recommended pattern)

**Usage:**

1. Import the collection into Postman.
2. Set the collection variable `baseUrl` to your deployed API Gateway invoke URL
   (available after `syndicate deploy`, or in the AWS Console under API Gateway
   → Stages).
3. Run **Auth → sign-up**, then **Auth → sign-in** to populate `idToken`,
   `accessToken`, and `refreshToken` collection variables automatically (via
   the request's post-response script).
4. Try the three object-listing requests as-is, and then experiment by
   manually swapping the `Authorization` header value between `{{idToken}}`
   and `{{accessToken}}` on each request to reproduce the `401` responses
   described in the OpenAPI spec.

## Contributing

Contributions, fixes and improvements are welcome. Please open issues or pull requests against the main repository: https://github.com/epam/aws-syndicate

## License

See the repository LICENSE file for licensing information.
