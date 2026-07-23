/*
 * Copyright 2026 EPAM Systems, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.demoapigatewaycognito.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import org.json.JSONObject;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;

public class PostSignOutHandler extends CognitoSupport implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

    public PostSignOutHandler(CognitoIdentityProviderClient cognitoClient) {
        super(cognitoClient);
    }

    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent requestEvent, Context context) {
        try {
            // The Cognito authorizer already validated the Access Token;
            // its `username` claim is surfaced by API Gateway in the request context.
            String username = requestEvent.getRequestContext().getAuthorizer().get("claims") instanceof java.util.Map<?, ?> claims
                    ? (String) claims.get("username")
                    : null;
            if (username == null) {
                return new APIGatewayProxyResponseEvent()
                        .withStatusCode(401)
                        .withBody(new JSONObject().put("message", "Unauthorized").toString());
            }
            cognitoSignOut(username);
            return new APIGatewayProxyResponseEvent().withStatusCode(204);
        } catch (Exception e) {
            return new APIGatewayProxyResponseEvent()
                    .withStatusCode(401)
                    .withBody(new JSONObject().put("message", e.getMessage()).toString());
        }
    }
}
