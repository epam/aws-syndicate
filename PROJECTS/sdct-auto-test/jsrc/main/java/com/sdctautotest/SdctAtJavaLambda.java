package com.sdctautotest;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.annotations.lambda.Tag;
import com.syndicate.deployment.annotations.lambda.Tags;
import com.syndicate.deployment.annotations.events.RuleEventSource;
import com.syndicate.deployment.model.ArtifactExtension;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RetentionSetting;

import java.util.HashMap;
import java.util.Map;

@LambdaHandler(
    lambdaName = "sdct-at-java-lambda",
	roleName = "sdct-at-java-lambda-role",
	isPublishVersion = true,
	aliasName = "${lambdas_alias_name}",
	logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
)

@LambdaLayer(
        layerName = "sdct-at-java-lambda_layer",
        libraries = {"sdct-at-java-lambda_layer/open-meteo-sdk-1.0.0.jar"},
        runtime = DeploymentRuntime.JAVA11,
        artifactExtension = ArtifactExtension.ZIP
)
@RuleEventSource(
        targetRule = "sdct-at-cw-rule"
)
@Tags(value = {
    @Tag(key = "tests", value = "smoke"),
    @Tag(key = "project", value = "sdct-auto-test")})

public class SdctAtJavaLambda implements RequestHandler<Object, Map<String, Object>> {

	public Map<String, Object> handleRequest(Object request, Context context) {
		System.out.println("Hello from lambda");
		Map<String, Object> resultMap = new HashMap<String, Object>();
		resultMap.put("statusCode", 200);
		resultMap.put("body", "Hello from Lambda");
		return resultMap;
	}
}
