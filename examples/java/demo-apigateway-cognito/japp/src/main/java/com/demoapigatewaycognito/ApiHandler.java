/*
 * Copyright 2024 EPAM Systems, Inc.
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
package com.demoapigatewaycognito;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.demoapigatewaycognito.dto.RouteKey;
import com.demoapigatewaycognito.handler.GetObjectsHandler;
import com.demoapigatewaycognito.handler.PostRefreshTokenHandler;
import com.demoapigatewaycognito.handler.PostSignInHandler;
import com.demoapigatewaycognito.handler.PostSignOutHandler;
import com.demoapigatewaycognito.handler.PostSignUpHandler;
import com.demoapigatewaycognito.handler.RouteNotImplementedHandler;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.environment.EnvironmentVariables;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.ResourceType;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;

import java.util.Map;

import static com.syndicate.deployment.model.environment.ValueTransformer.USER_POOL_NAME_TO_CLIENT_ID;
import static com.syndicate.deployment.model.environment.ValueTransformer.USER_POOL_NAME_TO_USER_POOL_ID;

@DependsOn(resourceType = ResourceType.COGNITO_USER_POOL, name = "${pool_name}")
@LambdaHandler(lambdaName = "api-handler",
        roleName = "api-handler-role",
        runtime = DeploymentRuntime.JAVA17,
        isPublishVersion = true,
        aliasName = "${lambdas_alias_name}")
@EnvironmentVariables(value = {
        @EnvironmentVariable(key = "REGION", value = "${region}"),
        @EnvironmentVariable(key = "COGNITO_ID", value = "${pool_name}", valueTransformer = USER_POOL_NAME_TO_USER_POOL_ID),
        @EnvironmentVariable(key = "CLIENT_ID", value = "${pool_name}", valueTransformer = USER_POOL_NAME_TO_CLIENT_ID)
})
public class ApiHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

    private final CognitoIdentityProviderClient cognitoClient;
    private final Map<RouteKey, RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent>> handlersByRouteKey;
    private final Map<String, String> corsHeaders;
    private final RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> routeNotImplementedHandler;

    public ApiHandler() {
        this.cognitoClient = CognitoIdentityProviderClient.builder()
                .region(Region.of(System.getenv("REGION")))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();
        this.handlersByRouteKey = initHandlers();
        this.corsHeaders = Map.of(
                "Access-Control-Allow-Headers", "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Origin", "*",
                "Access-Control-Allow-Methods", "*",
                "Accept-Version", "*"
        );
        this.routeNotImplementedHandler = new RouteNotImplementedHandler();
    }

    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent requestEvent, Context context) {
        return handlersByRouteKey
                .getOrDefault(new RouteKey(requestEvent.getHttpMethod(), requestEvent.getPath()), routeNotImplementedHandler)
                .handleRequest(requestEvent, context)
                .withHeaders(corsHeaders);
    }

    private Map<RouteKey, RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent>> initHandlers() {
        GetObjectsHandler getObjects = new GetObjectsHandler();
        return Map.of(
                new RouteKey("POST", "/auth/sign-up"),       new PostSignUpHandler(cognitoClient),
                new RouteKey("POST", "/auth/sign-in"),       new PostSignInHandler(cognitoClient),
                new RouteKey("POST", "/auth/refresh-token"), new PostRefreshTokenHandler(cognitoClient),
                new RouteKey("POST", "/auth/sign-out"),      new PostSignOutHandler(cognitoClient),
                new RouteKey("GET",  "/objects/public"),                 getObjects,
                new RouteKey("GET",  "/objects/secured-by-id-token"),    getObjects,
                new RouteKey("GET",  "/objects/secured-by-access-token"), getObjects
        );
    }
}
