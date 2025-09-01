package com.sdctautotest;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.annotations.tag.Tag;
import com.syndicate.deployment.annotations.tag.Tags;
import com.syndicate.deployment.annotations.events.RuleEventSource;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.environment.EnvironmentVariables;
import com.syndicate.deployment.model.ArtifactExtension;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RetentionSetting;
import com.syndicate.deployment.model.environment.ValueTransformer;

import java.util.HashMap;
import java.util.Map;

@EnvironmentVariables(value = {
        @EnvironmentVariable(key = "ENDPOINT", value = "sdct-at-rds-db-cluster", valueTransformer = ValueTransformer.RDS_DB_CLUSTER_NAME_TO_ENDPOINT),
        @EnvironmentVariable(key = "MASTER_CREDENTIALS_SECRET_NAME", value = "sdct-at-rds-db-cluster", valueTransformer = ValueTransformer.RDS_DB_CLUSTER_NAME_TO_MASTER_USER_SECRET_NAME)
})

@LambdaHandler(
    lambdaName = "sdct-at-java-lambda",
	roleName = "sdct-at-java-lambda-role",
	isPublishVersion = true,
	aliasName = "${lambdas_alias_name}",
	logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED
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
