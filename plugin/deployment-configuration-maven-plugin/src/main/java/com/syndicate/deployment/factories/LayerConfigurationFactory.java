package com.syndicate.deployment.factories;

import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.model.Architecture;
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
			.withRuntimes(layerDefinition.runtime()).build();

		String description = layerDefinition.description();
		if (!description.equals("")) {
			configuration.setDescription(description);
		}

		String licence = layerDefinition.licence();
		if (!licence.equals("")) {
			configuration.setLicence(licence);
		}

		String[] libraries = layerDefinition.libraries();
		if (libraries.length > 0) {
			configuration.setLibraries(libraries);
		}

		Architecture[] architectures = layerDefinition.architectures();
		if (architectures.length > 0) {
			configuration.setArchitectures(architectures);
		}

		return configuration;
	}

}
