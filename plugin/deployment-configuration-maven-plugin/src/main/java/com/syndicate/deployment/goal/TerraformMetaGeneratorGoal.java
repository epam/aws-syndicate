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
package com.syndicate.deployment.goal;

import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.LayerConfiguration;
import com.syndicate.deployment.api.model.request.SyndicateCredentials;
import com.syndicate.deployment.model.terraform.TerraformLambdaConfiguration;
import com.syndicate.deployment.model.terraform.TerraformLambdaVpcConfig;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Created by Oleksandr Onsha on 10/25/18
 */
@Mojo(name = "gen-terraform-config", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class TerraformMetaGeneratorGoal extends SyndicateMetaGeneratorGoal {

	private static final String ARN_SEPARATOR = ":";
	private static final String TERRAFORM_CONFIGURATION_FILE_NAME = "deployment_resources.tf.json";
	private static final String IAM_ROLE_ARN_PREFIX = "arn:aws:iam::";
	private static final String IAM_ROLE_ARN_SUFFIX = ":role/";
	private static final String ARN_PREFIX = "arn:aws:";

	@Parameter
	private String accountId;

	@Parameter
	private String region;

	private static String buildIamRoleArn(String roleName, String accountId) {
		return IAM_ROLE_ARN_PREFIX + accountId + IAM_ROLE_ARN_SUFFIX + roleName;
	}

	private static String buildDeadLetterSourceArn(String dlResourceName, String type, String accountId, String region) {
		return ARN_PREFIX + type + ARN_SEPARATOR + region + ARN_SEPARATOR + accountId + ARN_SEPARATOR + dlResourceName;
	}

	public String getAccountId() {
		return accountId;
	}

	public void setAccountId(String accountId) {
		this.accountId = accountId;
	}

	public String getRegion() {
		return region;
	}

	public void setRegion(String region) {
		this.region = region;
	}

	@Override
	public String getDeploymentResourcesFileName() {
		return TERRAFORM_CONFIGURATION_FILE_NAME;
	}

	@Override
	protected Map<String, Object> convertConfiguration(Map<String, LambdaConfiguration> lambdaConfiguration,
	                                                   Map<String, LayerConfiguration> layerConfiguration) {
		// TODO: 2019-12-03 implement conversion of Lambda Layers
		Map<String, TerraformLambdaConfiguration> terraformLambdas = convertLambdaSyndicateToTerraformConfiguration(lambdaConfiguration, accountId, region);
		Map<String, Object> terraformConfiguration = new HashMap<>(2); // provider + resource
		terraformConfiguration.put("provider",
			Collections.singletonMap("aws",
				Collections.singletonMap("region", region)));
		terraformConfiguration.put("resource",
			Collections.singletonMap("aws_lambda_function",
				terraformLambdas));
		return terraformConfiguration;
	}


	@Override
	public void uploadMeta(Map<String, Object> configurations, SyndicateCredentials credentials) {
		// do nothing
	}

	private Map<String, TerraformLambdaConfiguration> convertLambdaSyndicateToTerraformConfiguration(
		Map<String, LambdaConfiguration> syndicateConfiguration, String accountId, String region) {
		Map<String, TerraformLambdaConfiguration> lambdaResourcesMap = new HashMap<>(
			syndicateConfiguration.size() + 1); // lambda resources + provider

		for (Map.Entry<String, LambdaConfiguration> entry : syndicateConfiguration.entrySet()) {
			// Building TerraformLambdaConfiguration
			LambdaConfiguration syndicate = entry.getValue();
			String lambdaName = entry.getKey();
			TerraformLambdaConfiguration.Builder configurationBuilder = TerraformLambdaConfiguration.builder()
				.withDeploymentPackageName(syndicate.getPath() + "/target/" + syndicate.getPackageName())
				.withFunctionName(lambdaName)
				.withHandler(syndicate.getFunction())
				.withRole(buildIamRoleArn(syndicate.getRole(), this.accountId))
				.withMemorySize(syndicate.getMemory())
				.withTimeout(syndicate.getTimeout())
				.withRuntime(syndicate.getRuntime())
				.withPublishNewVersion(syndicate.isPublishVersion());
			if (syndicate.getSubnetIds() != null && syndicate.getSubnetIds().length != 0
				&& syndicate.getSecurityGroupIds() != null && syndicate.getSecurityGroupIds().length != 0) {
				TerraformLambdaVpcConfig config = TerraformLambdaVpcConfig.builder()
					.withSubnetIds(syndicate.getSubnetIds())
					.withSecurityGroupIds(syndicate.getSecurityGroupIds())
					.build();
				configurationBuilder.withVpcConfig(config);
			}
			if (syndicate.getVariables() != null && !syndicate.getVariables().isEmpty()) {
				configurationBuilder.withEnvironmentVariables(syndicate.getVariables());
			}
			if (syndicate.getDlResourceName() != null && syndicate.getDlResourceType() != null) {
				configurationBuilder.withDeadLetterConfig(buildDeadLetterSourceArn(syndicate.getDlResourceName(),
					syndicate.getDlResourceType(), accountId, region));
			}
			lambdaResourcesMap.put(lambdaName, configurationBuilder.build());
		}
		return lambdaResourcesMap;
	}
}
