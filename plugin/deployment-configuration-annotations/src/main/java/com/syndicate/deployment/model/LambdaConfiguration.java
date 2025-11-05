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

package com.syndicate.deployment.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.syndicate.deployment.model.events.EventSourceItem;
import com.syndicate.deployment.model.lambda.url.UrlConfig;

import java.security.InvalidParameterException;
import java.util.Arrays;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class LambdaConfiguration {

    @JsonProperty("name")
    private String name;

    @JsonProperty("lambda_path")
    private String path;

    @JsonProperty("version")
    private String version;

    @JsonProperty("func_name")
    private String function;

    @JsonProperty("deployment_package")
    private String packageName;

    @JsonProperty("max_concurrency")
    private Integer concurrentExecutions;

    @JsonProperty("provisioned_concurrency")
    private ProvisionedConcurrency provisionedConcurrency;

    @JsonProperty("resource_type")
    private ResourceType resourceType;

    @JsonProperty("runtime")
    private DeploymentRuntime runtime;

    @JsonProperty("architectures")
    private Architecture[] architectures;

    @JsonProperty("iam_role_name")
    private String role;

    @JsonProperty("memory")
    private long memory;

    @JsonProperty("timeout")
    private long timeout;

    @JsonProperty("region")
    private String region;

    @JsonProperty("subnet_ids")
    private String[] subnetIds;

    @JsonProperty("security_group_ids")
    private String[] securityGroupIds;

    @JsonProperty("dependencies")
    private Set<DependencyItem> dependencies;

    @JsonProperty("event_sources")
    private Set<EventSourceItem> eventSources;

    @JsonProperty("env_variables")
    private Map<String, Object> variables;

    @JsonProperty("tags")
    private Map<String, String> tags;

    @JsonProperty("dl_resource_name")
    private String dlResourceName;

    @JsonProperty("dl_resource_type")
    private String dlResourceType;

    @JsonProperty("tracing_mode")
    private String tracingMode;

    @JsonProperty("publish_version")
    private boolean isPublishVersion;

    @JsonProperty("alias")
    private String alias;

    @JsonProperty("layers")
    private String[] layers;

    @JsonProperty("logs_expiration")
    private String logsExpiration;

    @JsonProperty("snap_start")
    private LambdaSnapStart snapStart;

    @JsonProperty("resource_group")
    private String resourceGroup;

    @JsonProperty("url_config")
    private UrlConfig urlConfig;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPath() {
        return path;
    }

    public String getVersion() {
        return version;
    }

    public String getFunction() {
        return function;
    }

    public String getPackageName() {
        return packageName;
    }

    public Integer getConcurrentExecutions() {
        return concurrentExecutions;
    }

    public void setConcurrentExecutions(Integer concurrentExecutions) {
        this.concurrentExecutions = concurrentExecutions;
    }

    public ProvisionedConcurrency getProvisionedConcurrency() {
        return provisionedConcurrency;
    }

    public void setProvisionedConcurrency(ProvisionedConcurrency provisionedConcurrency) {
        this.provisionedConcurrency = provisionedConcurrency;
    }

    public ResourceType getResourceType() {
        return resourceType;
    }

    public DeploymentRuntime getRuntime() {
        return runtime;
    }

    public Architecture[] getArchitectures() {
        return architectures;
    }

    public String getRole() {
        return role;
    }

    public long getMemory() {
        return memory;
    }

    public long getTimeout() {
        return timeout;
    }

    public Set<DependencyItem> getDependencies() {
        return dependencies;
    }

    public Set<EventSourceItem> getEventSources() {
        return eventSources;
    }

    public Map<String, Object> getVariables() {
        return variables;
    }

    public Map<String, String> getTags() {
        return tags;
    }

    public String getDlResourceName() {
        return dlResourceName;
    }

    public void setDlResourceName(String dlResourceName) {
        this.dlResourceName = dlResourceName;
    }

    public String getDlResourceType() {
        return dlResourceType;
    }

    public void setDlResourceType(String dlResourceType) {
        this.dlResourceType = dlResourceType;
    }

    public String getTracingMode() {
        return tracingMode;
    }

    public void setTracingMode(String tracingMode) {
        this.tracingMode = tracingMode;
    }

    @JsonIgnore
    public boolean isPublishVersion() {
        return isPublishVersion;
    }

    public void setPublishVersion(boolean publishVersion) {
        isPublishVersion = publishVersion;
    }

    public String getAlias() {
        return alias;
    }

    public void setAlias(String alias) {
        this.alias = alias;
    }

    public String[] getSubnetIds() {
        return subnetIds;
    }

    public void setSubnetIds(String[] subnetIds) {
        this.subnetIds = subnetIds;
    }

    public String[] getSecurityGroupIds() {
        return securityGroupIds;
    }

    public void setSecurityGroupIds(String[] securityGroupIds) {
        this.securityGroupIds = securityGroupIds;
    }

    public String[] getLayers() {
        return layers;
    }

    public void setLayers(String[] layers) {
        this.layers = layers;
    }

    public void setLogsExpiration(String logsExpiration) {
        this.logsExpiration = logsExpiration;
    }

    public LambdaSnapStart getSnapStart() {
        return snapStart;
    }

    public void setSnapStart(LambdaSnapStart snapStart) {
        this.snapStart = snapStart;
    }

    public void setUrlConfig(UrlConfig urlConfig) {
        this.urlConfig = urlConfig;
    }

    public static class Builder {

        private final LambdaConfiguration configuration = new LambdaConfiguration();

        public Builder withName(String name) {
            Objects.requireNonNull(name, "Name cannot be null");
            configuration.name = name;
            return this;
        }

        public Builder withPath(String path) {
            Objects.requireNonNull(path, "Path cannot be null");
            configuration.path = path;
            return this;
        }

        public Builder withVersion(String version) {
            Objects.requireNonNull(version, "Version cannot be null");
            configuration.version = version;
            return this;
        }

        public Builder withFunction(String function) {
            Objects.requireNonNull(function, "Function cannot be null");
            configuration.function = function;
            return this;
        }

        public Builder withRegionScope(RegionScope regionScope) {
            Objects.requireNonNull(regionScope, "region scope cannot be null");
            configuration.region = regionScope.getName();
            return this;
        }

        public Builder withPackageName(String path) {
            Objects.requireNonNull(path, "Path cannot be null");
            configuration.packageName = path;
            return this;
        }

        public Builder withConcurrentExecutions(Integer concurrentExecutions) {
            Objects.requireNonNull(concurrentExecutions, "Сoncurrent executions cannot be null");
            configuration.concurrentExecutions = concurrentExecutions;
            return this;
        }

        public Builder withProvisionedConcurrency(ProvisionedConcurrency provisionedConcurrency) {
            Objects.requireNonNull(provisionedConcurrency, "Provisioned concurrency configuration object cannot be null");
            configuration.provisionedConcurrency = provisionedConcurrency;
            return this;
        }

        public Builder withResourceType(ResourceType resourceType) {
            Objects.requireNonNull(resourceType, "ResourceType cannot be null");
            configuration.resourceType = resourceType;
            return this;
        }

        public Builder withRuntime(DeploymentRuntime deploymentRuntime) {
            Objects.requireNonNull(deploymentRuntime, "DeploymentRuntime cannot be null");
            configuration.runtime = deploymentRuntime;
            return this;
        }

        public Builder withArchitectures(Architecture[] architectures) {
            Objects.requireNonNull(architectures, "Architecture cannot be null");
            configuration.architectures = architectures;
            return this;
        }

        public Builder withRole(String role) {
            Objects.requireNonNull(role, "Role cannot be null");
            configuration.role = role;
            return this;
        }

        public Builder withMemory(long memory) {
            if (memory <= 0) {
                throw new InvalidParameterException("Memory cannot be negative or 0");
            }
            configuration.memory = memory;
            return this;
        }

        public Builder withTimeout(long timeout) {
            if (timeout <= 0) {
                throw new InvalidParameterException("Timeout cannot be negative or 0");
            }
            configuration.timeout = timeout;
            return this;
        }

        public Builder withDependencies(Set<DependencyItem> dependencies) {
            Objects.requireNonNull(dependencies, "Dependencies cannot be null");
            configuration.dependencies = dependencies;
            return this;
        }

        public Builder withEventSources(Set<EventSourceItem> events) {
            Objects.requireNonNull(events, "Events cannot be null");
            configuration.eventSources = events;
            return this;
        }

        public Builder withVariables(Map<String, Object> variables) {
            Objects.requireNonNull(variables, "Variables cannot be null");
            configuration.variables = variables;
            return this;
        }

        public Builder withTags(Map<String, String> tags) {
            Objects.requireNonNull(tags, "Tags cannot be null");
            configuration.tags = tags;
            return this;
        }


        public Builder withTracingMode(String tracingMode) {
            Objects.requireNonNull(tracingMode, "Tracing mode cannot be null");
            configuration.tracingMode = tracingMode;
            return this;
        }

        public Builder withDlResourceName(String dlResourceName) {
            Objects.requireNonNull(dlResourceName, "DL Resource name cannot be null");
            configuration.dlResourceName = dlResourceName;
            return this;
        }

        public Builder withDlResourceType(String dlResourceType) {
            Objects.requireNonNull(dlResourceType, "DL Resource type cannot be null");
            configuration.dlResourceType = dlResourceType;
            return this;
        }

        public Builder withSubnetIds(String[] subnetIds) {
            Objects.requireNonNull(subnetIds, "Subnet ids cannot be null");
            configuration.subnetIds = subnetIds;
            return this;
        }

        public Builder withSecurityGroupIds(String[] securityGroupIds) {
            Objects.requireNonNull(securityGroupIds, "Security group ids cannot be null");
            configuration.securityGroupIds = securityGroupIds;
            return this;
        }

        public Builder withPublishVersion(boolean isPublishVersion) {
            configuration.isPublishVersion = isPublishVersion;
            return this;
        }

        public Builder withAlias(String alias) {
            if (configuration.alias != null && alias.equals("")) {
                throw new InvalidParameterException("Alias cannot be empty");
            }
            configuration.alias = alias;
            return this;
        }

        public Builder withLayers(String[] layers) {
        	Objects.requireNonNull(layers, "Array of layers names cannot be null");
        	configuration.layers = layers;
        	return this;
        }

        public Builder withSnapStart(LambdaSnapStart snapStart) {
            configuration.snapStart = snapStart;
            return this;
        }

        public Builder withResourceGroup(String resourceGroup) {
            if (resourceGroup != null && !resourceGroup.isEmpty()){
                configuration.resourceGroup = resourceGroup;
            }
            return this;
        }

        public Builder withLogsExpirations(String logsExpirations) {
            configuration.logsExpiration = logsExpirations;
            return this;
        }

        public LambdaConfiguration build() {
            Objects.requireNonNull(configuration.name, "Name cannot be null");
            Objects.requireNonNull(configuration.path, "Path cannot be null");
            Objects.requireNonNull(configuration.version, "Version cannot be null");
            Objects.requireNonNull(configuration.function, "Function cannot be null");
            Objects.requireNonNull(configuration.packageName, "Package name cannot be null");
            Objects.requireNonNull(configuration.resourceType, "ResourceType cannot be null");
            Objects.requireNonNull(configuration.runtime, "DeploymentRuntime cannot be null");
            Objects.requireNonNull(configuration.architectures, "Architecture cannot be null");
            Objects.requireNonNull(configuration.role, "Role cannot be null");
            if (configuration.memory <= 0) {
                throw new InvalidParameterException("Memory cannot be negative or 0");
            }
            if (configuration.timeout <= 0) {
                throw new InvalidParameterException("Timeout cannot be negative or 0");
            }
            Objects.requireNonNull(configuration.dependencies, "Dependencies cannot be null");
            Objects.requireNonNull(configuration.eventSources, "Events cannot be null");
            Objects.requireNonNull(configuration.variables, "Variables cannot be null");
            Objects.requireNonNull(configuration.tags, "Tags cannot be null");
            Objects.requireNonNull(configuration.subnetIds, "Subnet ids cannot be null");
            Objects.requireNonNull(configuration.securityGroupIds, "Security group ids cannot be null");
            if (configuration.alias != null && configuration.alias.equals("")) {
                throw new InvalidParameterException("Alias cannot be empty");
            }
            return configuration;
        }

    }

    @Override
    public String toString() {
        return "LambdaConfiguration{" +
                "name='" + name + '\'' +
                "path='" + path + '\'' +
                ", version='" + version + '\'' +
                ", function='" + function + '\'' +
                ", packageName='" + packageName + '\'' +
                ", concurrentExecutions=" + concurrentExecutions +
                ", resourceType=" + resourceType +
                ", runtime=" + runtime +
                ", architectures=" + Arrays.toString(architectures) +
                ", role='" + role + '\'' +
                ", memory=" + memory +
                ", timeout=" + timeout +
                ", region='" + region + '\'' +
                ", subnetIds=" + Arrays.toString(subnetIds) +
                ", securityGroupIds=" + Arrays.toString(securityGroupIds) +
                ", dependencies=" + dependencies +
                ", eventSources=" + eventSources +
                ", variables=" + variables +
                ", tags=" + tags +
                ", dlResourceName='" + dlResourceName + '\'' +
                ", dlResourceType='" + dlResourceType + '\'' +
                ", tracingMode='" + tracingMode + '\'' +
                ", alias='" + alias + '\'' +
                ", urlConfig='" + urlConfig + '\'' +
                '}';
    }
}
