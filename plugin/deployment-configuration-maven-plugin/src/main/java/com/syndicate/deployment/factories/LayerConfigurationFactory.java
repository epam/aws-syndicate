package com.syndicate.deployment.factories;

import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.LayerConfiguration;
import com.syndicate.deployment.model.ResourceType;

/**
 * Created by Oleksandr Onsha on 2019-12-03
 */
public class LayerConfigurationFactory {


	public static LayerConfiguration createLayerConfiguration(LambdaLayer layerDefinition) {

		LayerConfiguration configuration = new LayerConfiguration.Builder()
			.withName(layerDefinition.layerName())
			.withDeploymentPackage(layerDefinition.layerName() + "-assembly"
                    + layerDefinition.artifactExtension().getExtension()) // TODO: 2019-12-03 how to get assembly id here?
			.withResourceType(ResourceType.LAMBDA_LAYER)
			.withRuntimes(DeploymentRuntime.JAVA8).build();

		String description = layerDefinition.description();
		if (!description.equals("")) {
			configuration.setDescription(description);
		}

		String licence = layerDefinition.licence();
		if (!licence.equals("")) {
			configuration.setLicence(licence);
		}
		return configuration;
	}

}
