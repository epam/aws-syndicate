package com.aws.lambda.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.aws.lambda.response.ErrorMessage;
import com.aws.lambda.response.HelloMessage;
import com.google.gson.Gson;
import com.syndicate.deployment.annotations.LambdaUrlConfig;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.model.Architecture;
import com.syndicate.deployment.model.ArtifactExtension;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.lambda.url.AuthType;
import com.syndicate.deployment.model.lambda.url.InvokeMode;
import org.apache.commons.lang3.StringUtils;

import java.util.Map;
import java.util.Optional;

@LambdaHandler(
        lambdaName = "hello-lambda",
        roleName = "hello-lambda-role",
        layers = {"sdk-layer"},
        runtime = DeploymentRuntime.JAVA11,
        architecture = Architecture.ARM64
)
@LambdaLayer(
        layerName = "sdk-layer",
        libraries = {"lib/commons-lang3-3.14.0.jar", "lib/gson-2.10.1.jar"},
        runtime = DeploymentRuntime.JAVA8,
        artifactExtension = ArtifactExtension.ZIP
)
@LambdaUrlConfig(
        authType = AuthType.NONE,
        invokeMode = InvokeMode.BUFFERED
)
public class HelloHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

    private static final int SC_OK = 200;
    private static final int SC_BAD_REQUEST = 400;
    private final Gson gson = new Gson();

    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent apiGatewayProxyRequestEvent, Context context) {
        context.getLogger().log(apiGatewayProxyRequestEvent.toString());
        Map<String, String> queryStringParameters = apiGatewayProxyRequestEvent.getQueryStringParameters();
        try {
            return new APIGatewayProxyResponseEvent()
                    .withStatusCode(SC_OK)
                    .withBody(gson.toJson(new HelloMessage(String.format("Hello, %s", getUserName(queryStringParameters)))));
        } catch (IllegalArgumentException exception) {
            return new APIGatewayProxyResponseEvent()
                    .withStatusCode(SC_BAD_REQUEST)
                    .withBody(gson.toJson(new ErrorMessage(exception.getMessage())));
        }
    }

    private String getUserName(Map<String, String> queryStringParameters) {
        return Optional.ofNullable(queryStringParameters)
                .map(params -> params.get("user"))
                .filter(StringUtils::isNotEmpty)
                .orElseThrow(() -> new IllegalArgumentException("the query string parameter 'user' has not been specified"));
    }

}
