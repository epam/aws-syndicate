# lambda-cognito-api-gateway-oauth-scopes

A Syndicate example that deploys:

- A Python Lambda function
- An IAM role and custom policy for the Lambda
- An API Gateway fronting the Lambda
- A Cognito User Pool

Authentication overview: This example demonstrates three API security approaches (public, ID token, access token) using Amazon Cognito. No custom Resource Server is configured — the built-in `aws.cognito.signin.user.admin` scope is used to illustrate token and scope behavior. See the [API Documentation](#api-documentation) section for full details.

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Build & Deploy](#build--deploy)
- [Local modules](#local-modules)
- [Cleanup](#cleanup)
- [API Documentation](#api-documentation)
- [Postman Collection](#postman-collection)

---

## Prerequisites

- Syndicate CLI installed and available on PATH
- AWS credentials configured (via environment or AWS CLI)
- A unique S3 bucket for storing deployment artifacts

## Configuration

1. Update `syndicate.yml` placeholders:
   - `ACCOUNT_ID` — AWS account ID that will host the demo
   - `REGION` — AWS region for deployment
   - `YOUR_BUCKET_NAME` — S3 bucket for artifacts (must be globally unique)
   - `YOUR_PATH` — absolute path to this project folder

2. Update `syndicate_aliases.yml` placeholders:
   - `ACCOUNT_ID` — same AWS account
   - `REGION` — same AWS region
   - `USERPOOL_NAME` — desired Cognito User Pool name

3. Export configuration folder via `SDCT_CONF`:

Unix/macOS (bash/zsh):

```bash
export SDCT_CONF=$YOUR_PATH/.syndicate-config-lambda-cognito-api-gateway-oauth-scopes
```

Windows (PowerShell):

```powershell
$env:SDCT_CONF = "$YOUR_PATH\.syndicate-config-lambda-cognito-api-gateway-oauth-scopes"
```

## Build & Deploy

From the project root:

```bash
syndicate build
syndicate deploy
```

After deploy, the API Gateway and Cognito resources will be provisioned as defined in `deployment_resources.json`.

API URL scheme:

```
https://{api-id}.execute-api.{region}.amazonaws.com/api/{endpoint}
```

Example sign-up request:

```bash
curl -X POST "https://{api-id}.execute-api.{region}.amazonaws.com/api/auth/sign-up" \
  -H "Content-Type: application/json" \
  -d '{"username":"jdoe","password":"P@ssw0rd","email":"jdoe@example.com"}'
```

## Local modules

Shared code lives under `pyapp/src/commons/` and is bundled into the Lambda via `local_requirements.txt`:

```
pyapp/src/
├── commons/
│   ├── __init__.py
│   ├── constants.py      # CORS headers, sample object data
│   └── http_utils.py     # API Gateway response helpers
└── lambdas/
    └── lambda_example/
        ├── handler.py
        ├── local_requirements.txt
        └── requirements.txt
```

`local_requirements.txt` lists local package names (one per line) that Syndicate copies into the deployment bundle alongside the handler.
`requirements.txt` lists external PyPI dependencies (`boto3`). During `syndicate build`, both files are resolved independently — local modules from `pyapp/src/`, external libraries from the package index.

The handler imports shared utilities from the local package:

```python
from http import HTTPStatus

from commons import build_response, parse_body, SAMPLE_OBJECTS

return build_response(HTTPStatus.OK, SAMPLE_OBJECTS)
```

## Cleanup

To remove the resources created by this example:

```bash
syndicate clean
```

## API Documentation

### OpenAPI Specification

The full API contract — including the intentional Cognito authorizer token validation behavior — is documented in [`docs/open-api.yaml`](./docs/open-api.yaml).

Deployment note: the API Gateway authorizer and per-method security are defined in `deployment_resources.json`. That file configures three approaches illustrated by the example endpoints:

- **Public:** `/objects/public` has no authorizer and allows anonymous access.
- **ID Token (antipattern):** `/objects/secured-by-id-token` attaches the Cognito authorizer but does **not** set `authorization_scopes`. API Gateway treats the bearer token as an **ID Token** and validates the `aud` claim against the App Client ID.
- **Access Token (recommended):** `/objects/secured-by-access-token` attaches the Cognito authorizer and sets `authorization_scopes` to `aws.cognito.signin.user.admin`. API Gateway validates the bearer token as an **Access Token** and checks the `scope` claim.

Configuration examples from `deployment_resources.json` (trimmed):

```json
{
  "syndicate-demo-api": {
    "authorizers": {
      "authorizer": {
        "type": "COGNITO_USER_POOLS",
        "identity_source": "method.request.header.Authorization",
        "user_pools": ["${userpool_name}"],
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
      "lambda_name": "lambda_example"
    }
  }
}
```

ID Token (authorizer attached, no scopes):

```json
{
  "/objects/secured-by-id-token": {
    "GET": {
      "authorization_type": "authorizer",
      "integration_type": "lambda",
      "lambda_name": "lambda_example"
    }
  }
}
```

Access Token (authorizer + `authorization_scopes`):

```json
{
  "/objects/secured-by-access-token": {
    "GET": {
      "authorization_type": "authorizer",
      "authorization_scopes": [
        "aws.cognito.signin.user.admin"
      ],
      "integration_type": "lambda",
      "lambda_name": "lambda_example"
    }
  }
}
```

Preview the spec locally:

```bash
npm install -g swagger-ui-watcher
swagger-ui-watcher docs/open-api.yaml
```

### CORS and browser preflight

Browsers send an automatic `OPTIONS` preflight for cross-origin requests with `Content-Type: application/json` or `Authorization` headers. Auth endpoints in this example enable CORS in `deployment_resources.json` so browser-based clients and Swagger UI can reach them.

### Authentication & Resource Server

This sample does not set up a custom Resource Server. Instead, it uses the built-in `aws.cognito.signin.user.admin` scope to demonstrate ID, Access, and Refresh token behavior. This scope is provided by Amazon Cognito by default.

## Postman Collection

A ready-to-use Postman collection is provided at [`docs/postman/lambda-cognito-api-gateway-oauth-scopes.postman_collection.json`](./docs/postman/lambda-cognito-api-gateway-oauth-scopes.postman_collection.json).

**Usage:**

1. Import the collection into Postman.
2. Set the collection variable `baseUrl` to your deployed API Gateway invoke URL (stage `api`).
3. Run **Auth → sign-up**, then **Auth → sign-in**. Sign-in automatically stores `idToken`, `accessToken`, and `refreshToken`.
4. Try the three object-listing requests. Set `bearerToken` to `{{idToken}}` or `{{accessToken}}` to reproduce the `401` responses described in the OpenAPI spec:
   - `/objects/secured-by-id-token` — works with `idToken`, fails with `accessToken`
   - `/objects/secured-by-access-token` — works with `accessToken`, fails with `idToken`
