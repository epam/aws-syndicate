/*
 * Copyright 2018 EPAM Systems, Inc.
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

package com.demolayerurl.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayV2HTTPEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayV2HTTPResponse;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.annotations.lambda.LambdaUrlConfig;
import com.syndicate.deployment.model.Architecture;
import com.syndicate.deployment.model.ArtifactExtension;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RetentionSetting;
import com.syndicate.deployment.model.lambda.url.AuthType;
import com.syndicate.deployment.model.lambda.url.InvokeMode;

import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

@LambdaHandler(
        lambdaName = "hello-lambda",
        roleName = "hello-lambda-role",
        layers = {"sdk-layer"},
        runtime = DeploymentRuntime.JAVA11,
        architecture = Architecture.ARM64,
        logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
)
@LambdaLayer(
        layerName = "sdk-layer",
        libraries = {"lib/commons-lang3-3.14.0.jar", "lib/gson-2.10.1.jar"},
        runtime = DeploymentRuntime.JAVA11,
        architectures = {Architecture.ARM64},
        artifactExtension = ArtifactExtension.ZIP
)
@LambdaUrlConfig(
        authType = AuthType.NONE,
        invokeMode = InvokeMode.BUFFERED
)
public class HelloHandler implements RequestHandler<APIGatewayV2HTTPEvent, APIGatewayV2HTTPResponse> {

    private static final int SC_OK = 200;
    private static final int SC_NOT_FOUND = 404;
    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private final Map<String, String> responseHeaders = Map.of("Content-Type", "application/json");
    private final Map<RouteKey, Function<APIGatewayV2HTTPEvent, APIGatewayV2HTTPResponse>> routeHandlers = Map.of(
            new RouteKey("GET", "/"), this::handleGetRoot,
            new RouteKey("GET", "/hello"), this::handleGetHello
    );

    @Override
    public APIGatewayV2HTTPResponse handleRequest(APIGatewayV2HTTPEvent requestEvent, Context context) {
        RouteKey routeKey = new RouteKey(getMethod(requestEvent), getPath(requestEvent));
        return routeHandlers.getOrDefault(routeKey, this::notFoundResponse).apply(requestEvent);
    }

    private APIGatewayV2HTTPResponse handleGetRoot(APIGatewayV2HTTPEvent requestEvent) {
        return buildResponse(SC_OK, Body.ok("Use the path /hello to get greetings message"));
    }

    private APIGatewayV2HTTPResponse handleGetHello(APIGatewayV2HTTPEvent requestEvent) {
        return buildResponse(SC_OK, Body.ok("Hello%s".formatted(
                Optional.ofNullable(requestEvent.getQueryStringParameters())
                        .map(this::getUserName)
                        .map(", %s"::formatted)
                        .orElse(" from lambda! Use the query string parameter 'name' to specify your name")
        )));
    }

    private APIGatewayV2HTTPResponse notFoundResponse(APIGatewayV2HTTPEvent requestEvent) {
        return buildResponse(SC_NOT_FOUND, Body.error("The resource with method %s and path %s is not found".formatted(
                getMethod(requestEvent),
                getPath(requestEvent)
        )));
    }

    private APIGatewayV2HTTPResponse buildResponse(int statusCode, Object body) {
        return APIGatewayV2HTTPResponse.builder()
                .withStatusCode(statusCode)
                .withHeaders(responseHeaders)
                .withBody(gson.toJson(body))
                .build();
    }

    private String getMethod(APIGatewayV2HTTPEvent requestEvent) {
        return requestEvent.getRequestContext().getHttp().getMethod();
    }

    private String getPath(APIGatewayV2HTTPEvent requestEvent) {
        return requestEvent.getRequestContext().getHttp().getPath();
    }

    private String getUserName(Map<String, String> queryStringParameters) {
        return queryStringParameters.get("name");
    }


    private record RouteKey(String method, String path) {
    }

    private record Body(String message, String error) {
        static Body ok(String message) {
            return new Body(message, null);
        }

        static Body error(String error) {
            return new Body(null, error);
        }
    }

}
