package com.syndicate.deployment.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.security.InvalidParameterException;
import java.util.Arrays;
import java.util.Objects;

/**
 * Created by Oleksandr Onsha on 2019-11-29
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class LayerConfiguration {

	@JsonProperty("name")
	private String name;

	@JsonProperty("description")
	private String description;

	@JsonProperty("runtimes")
	private DeploymentRuntime[] runtimes;

	@JsonProperty("resource_type")
	private ResourceType resourceType;

	@JsonProperty("licence")
	private String licence;

	@JsonProperty("deployment_package")
	private String deploymentPackage;

	@JsonProperty("libraries")
	private String[] libraries;

	@JsonProperty("architectures")
	private Architecture[] architectures;

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getDescription() {
		return description;
	}

	public void setDescription(String description) {
		this.description = description;
	}


	public String getLicence() {
		return licence;
	}

	public void setLicence(String licence) {
		this.licence = licence;
	}

	public String getDeploymentPackage() {
		return deploymentPackage;
	}

	public void setDeploymentPackage(String deploymentPackage) {
		this.deploymentPackage = deploymentPackage;
	}

	public String[] getLibraries() {
		return libraries;
	}

	public LayerConfiguration setLibraries(String[] libraries) {
		this.libraries = libraries;
		return this;
	}

	public DeploymentRuntime[] getRuntimes() {
		return runtimes;
	}

	public void setRuntimes(DeploymentRuntime[] runtimes) {
		this.runtimes = runtimes;
	}

	public Architecture[] getArchitectures() {
		return architectures;
	}

	public LayerConfiguration setArchitectures(Architecture[] architectures) {
		this.architectures = architectures;
		return this;
	}

	public static class Builder {
		private final LayerConfiguration layerConfiguration = new LayerConfiguration();

		public Builder() {
		}

		public Builder withName(String name) {
			Objects.requireNonNull(name, "Layer name cannot be null");
			if (name.isEmpty()) {
				throw new InvalidParameterException("Layer name cannot be empty");
			}
			layerConfiguration.setName(name);
			return this;
		}

		public Builder withDescription(String description) {
			Objects.requireNonNull(description, "Layer description cannot be null");
			if (description.isEmpty()) {
				throw new InvalidParameterException("Layer description cannot be empty");
			}
			layerConfiguration.setDescription(description);
			return this;
		}

		public Builder withRuntimes(DeploymentRuntime runtime) {
			Objects.requireNonNull(runtime, "Layer runtimes cannot be null");
			layerConfiguration.setRuntimes(new DeploymentRuntime[]{runtime});
			return this;
		}

		public Builder withLicence(String licence) {
			Objects.requireNonNull(licence, "Layer licence cannot be null");
			if (licence.isEmpty()) {
				throw new InvalidParameterException("Layer licence cannot be empty");
			}
			layerConfiguration.setLicence(licence);
			return this;
		}

		public Builder withDeploymentPackage(String deploymentPackage) {
			Objects.requireNonNull(deploymentPackage, "Layer deploymentPackage cannot be null");
			if (deploymentPackage.isEmpty()) {
				throw new InvalidParameterException("Layer deploymentPackage cannot be empty");
			}
			layerConfiguration.setDeploymentPackage(deploymentPackage);
			return this;
		}

		public Builder withResourceType(ResourceType resourceType) {
			Objects.requireNonNull(resourceType, "Resource type cannot be null");
			layerConfiguration.resourceType = resourceType;
			return this;
		}

		public LayerConfiguration build() {
			return this.layerConfiguration;
		}
	}
}
