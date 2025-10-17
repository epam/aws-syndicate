package com.example.lambda;

import java.util.Map;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.example.customsdk.RestServiceClient;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.annotations.lambda.LambdaUrlConfig;
import com.syndicate.deployment.model.Architecture;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RetentionSetting;

@LambdaHandler(
        runtime = DeploymentRuntime.JAVA17,
        lambdaName = "api-handler",
        roleName = "api-handler-role",
        isPublishVersion = true,
        layers = {"my-custom-libs"},
        aliasName = "${lambdas_alias_name}",
        logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
)
@LambdaLayer(
        layerName = "my-custom-libs",
        description = "Custom libraries layer",
        libraries = {"lambda/lib/custom-sdk.jar"},
        runtime = DeploymentRuntime.JAVA17,
        architectures = {Architecture.X86_64}
)
@LambdaUrlConfig()
public class ApiHandler implements RequestHandler<Object, Map<String, Object>> {
    @Override
    public Map<String, Object> handleRequest(Object request, Context context) {
        RestServiceClient client = new RestServiceClient();
        try {
            String url = "https://ifconfig.me/ip";
            return Map.of("lambda_public_ip", client.getFromUrl(url));
        } catch (Exception e) {
            return Map.of("error", e.getMessage());
        }
    }
}
