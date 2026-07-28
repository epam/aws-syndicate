# demo-apigateway-cognito

A small Syndicate example that deploys:
- A Java Lambda function
- An IAM role and custom policy for the Lambda
- An API Gateway fronting the Lambda
- A Cognito User Pool

Authentication overview: This example demonstrates three API security approaches (public, ID token, access token) using Amazon Cognito. No custom Resource Server is configured — the built-in `aws.cognito.signin.user.admin` scope is used to illustrate token and scope behavior. See the 'API Documentation' section for full details.

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Build & Deploy](#build--deploy)
- [Cleanup](#cleanup)
- [Notes](#notes)

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

- Replace placeholders carefully ACCOUNT_ID and BUCKET_NAME are critical for successful deployment.
- The PROJECT_FOLDER should point to the example project root so Syndicate can find sources and artifacts.

## API Documentation

### OpenAPI Specification

The full API contract — including the intentional Cognito authorizer token
validation behavior demonstrated by this example — is documented in
[`docs/open-api.yaml`](./docs/open-api.yaml).

Deployment note: the API Gateway authorizer and per-method security are
defined in `deployment_resources.json`. That file configures three approaches
illustrated by the example endpoints:

- Public: the `/objects/public` method is left unsecured (no authorizer) and
  allows anonymous access.
- ID Token (antipattern): `/objects/secured-by-id-token` attaches the Cognito
  authorizer but does not set `authorizationScopes` on the method. In this
  case API Gateway treats the bearer token as an **ID Token** and validates the
  `aud` claim against the App Client ID.
- Access Token (recommended): `/objects/secured-by-access-token` attaches the
  Cognito authorizer and configures `authorizationScopes` on the method. When
  `authorizationScopes` are present API Gateway validates the bearer token as
  an **Access Token** and checks the `scope` claim for the required scopes.

Configuration examples from `deployment_resources.json` (trimmed):

```json
{
  "api-gateway": {
    "authorizers": {
      "authorizer": {
        "type": "COGNITO_USER_POOLS",
        "identity_source": "method.request.header.Authorization",
        "user_pools": ["${pool_name}"],
        "ttl": 300
      }
    }
  }
}
```

Public method (no authorizer):

```json
{
  "/objects/public": {
    "GET": {
      "authorization_type": "NONE",
      "integration_type": "lambda",
      "lambda_name": "api-handler"
    }
  }
}
```

ID-Token (authorizer attached, no scopes — treated as ID Token):

```json
{
  "/objects/secured-by-id-token": {
    "GET": {
      "authorization_type": "authorizer",
      "integration_type": "lambda",
      "lambda_name": "api-handler"
    }
  }
}
```

Access-Token (authorizer + authorization_scopes — treated as Access Token):

```json
{
  "/objects/secured-by-access-token": {
    "GET": {
      "authorization_type": "authorizer",
      "authorization_scopes": [
        "aws.cognito.signin.user.admin"
      ],
      "integration_type": "lambda",
      "lambda_name": "api-handler"
    }
  }
}
```

See `deployment_resources.json` and `docs/open-api.yaml` for the full
configuration and additional context.

You can preview/explore the spec using any OpenAPI-compatible tool. For a lightweight local viewer install and run swagger-ui-watcher:

```bash
npm install -g swagger-ui-watcher
swagger-ui-watcher docs/open-api.yaml
```

CORS and browser preflight (why this matters):

Browsers block cross-origin requests by default. When a POST is sent with
Content-Type: application/json (or uses Authorization/custom headers), the
browser sends an automatic OPTIONS preflight to check allowed origins,
methods, and headers. If API Gateway isn't configured to respond to OPTIONS
with Access-Control-Allow-* headers, the preflight fails and the browser
blocks the real request — even though curl would still succeed.

Example CORS enablement (trimmed) from `deployment_resources.json`:

```json
{
  "/auth/sign-in": {
    "POST": {
      "enable_cors": {
        "state": true
      }
    }
  }
}
```

In short: enable CORS on methods that will be called from browser-based UIs
(or the Swagger UI) so API Gateway correctly handles preflight OPTIONS requests
and allows requests with JSON bodies and auth headers to reach your backend.

### Authentication & Resource Server

This sample does not set up a custom Resource Server. Instead, the example uses
the built-in `aws.cognito.signin.user.admin` scope to demonstrate ID, Access, and
Refresh token behavior. This scope is provided by Amazon Cognito by default and
enables client applications to make administrative and self-service requests
(for example, updating a user profile) directly to Cognito without additional
backend resource-server infrastructure.

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
3. Run **Auth → sign-up**, then **Auth → sign-in** to get `idToken`,
   `accessToken`, and `refreshToken`.
4. Try the three object-listing requests as-is, and then experiment by
   manually swapping the `Authorization` header value between `idToken`
   and `accessToken` on each request to reproduce the `401` responses
   described in the OpenAPI spec. (set the {{bearerToken}} variable in Postman to either `idToken` or `accessToken`).
