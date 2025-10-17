package com.example.lambda;

import java.util.Map;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.example.customsdk.RestServiceClient;
import com.syndicate.deployment.annotations.events.RuleEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.annotations.tag.Tag;
import com.syndicate.deployment.annotations.tag.Tags;
import com.syndicate.deployment.model.Architecture;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RetentionSetting;

@LambdaHandler(
        runtime = DeploymentRuntime.JAVA17,
        lambdaName = "sdct-at-java-lambda",
        roleName = "sdct-at-java-lambda-role",
        isPublishVersion = true,
        layers = {"sdct-at-java-lambda_layer"},
        aliasName = "${lambdas_alias_name}",
        logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
)
@LambdaLayer(
        layerName = "sdct-at-java-lambda_layer",
        description = "Custom libraries layer",
        libraries = {"lambda/lib/custom-sdk.jar"},
        runtime = DeploymentRuntime.JAVA17,
        architectures = {Architecture.X86_64}
)
@RuleEventSource(
        targetRule = "sdct-at-cw-rule"
)
@Tags(value = {
    @Tag(key = "tests", value = "smoke"),
    @Tag(key = "project", value = "sdct-auto-test")})
public class SdctAtJavaLambda implements RequestHandler<Object, Map<String, Object>> {

    private final RestServiceClient client = new RestServiceClient();

    @Override
    public Map<String, Object> handleRequest(Object request, Context context) {
        try {
            String url = "https://ifconfig.me/ip";
            return Map.of("lambda_public_ip", client.getFromUrl(url));
        } catch (Exception e) {
            return Map.of("error", e.getMessage());
        }
    }
}
