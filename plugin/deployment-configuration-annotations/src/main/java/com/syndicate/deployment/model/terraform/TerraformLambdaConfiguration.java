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
package com.syndicate.deployment.model.terraform;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.syndicate.deployment.model.DeploymentRuntime;

import java.security.InvalidParameterException;
import java.util.Collections;
import java.util.Map;
import java.util.Objects;

/**
 * Created by Oleksandr Onsha on 10/25/18
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class TerraformLambdaConfiguration {

    /*Properties to support in the nearest future
     * s3_bucket
     * s3_key
     * s3_object_version
     * dead_letter_config
     * reserved_concurrent_executions
     * kms_key_arn
     * source_code_hash
     *
     * source: https://www.terraform.io/docs/providers/aws/r/lambda_function.html
     * */

    @JsonProperty("filename")
    private String deploymentPackageName;

    @JsonProperty("function_name")
    private String functionName;

    @JsonProperty("handler")
    private String handler;

    @JsonProperty("role")
    private String roleArn;

    @JsonProperty("memory_size")
    private long memorySize;

    @JsonProperty("timeout")
    private long timeoutInSec;

    @JsonProperty("runtime")
    private DeploymentRuntime runtime;

    @JsonProperty("publish")
    private boolean publishNewVersion;

    @JsonProperty("vpc_config")
    private TerraformLambdaVpcConfig vpcConfig;

    @JsonProperty("environment")
    private Map<String, String> environmentVariables;

    @JsonProperty("dead_letter_config")
    private Map<String, String> deadLetterConfig;

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private static final String DL_CONFIG_ARN = "target_arn";
        private TerraformLambdaConfiguration configuration = new TerraformLambdaConfiguration();

        public Builder withDeploymentPackageName(String deploymentPackageName) {
            Objects.requireNonNull(deploymentPackageName, "Deployment package name cannot be null");
            configuration.deploymentPackageName = deploymentPackageName;
            return this;
        }

        public Builder withFunctionName(String functionName) {
            Objects.requireNonNull(functionName, "Function name cannot be null");
            configuration.functionName = functionName;
            return this;
        }

        public Builder withHandler(String handler) {
            Objects.requireNonNull(handler, "Function handler cannot be null");
            configuration.handler = handler;
            return this;
        }

        public Builder withRole(String roleArn) {
            Objects.requireNonNull(roleArn, "Role arn cannot be null");
            configuration.roleArn = roleArn;
            return this;
        }

        public Builder withMemorySize(long memorySize) {
            if (memorySize <= 0) {
                throw new InvalidParameterException("Memory cannot be negative or 0");
            }
            configuration.memorySize = memorySize;
            return this;
        }

        public Builder withRuntime(DeploymentRuntime runtime) {
            Objects.requireNonNull(runtime, "Deployment runtime cannot be null");
            configuration.runtime = runtime;
            return this;
        }

        public Builder withPublishNewVersion(boolean publishNewVersion) {
            configuration.publishNewVersion = publishNewVersion;
            return this;
        }

        public Builder withVpcConfig(TerraformLambdaVpcConfig config) {
            Objects.requireNonNull(config, "Lambda vpc vpcConfig cannot be null");
            configuration.vpcConfig = config;
            return this;
        }

        public Builder withEnvironmentVariables(Map<String, String> environmentVariables) {
            Objects.requireNonNull(environmentVariables, "Environment variables cannot be null");
            if (environmentVariables.isEmpty()) {
                throw new InvalidParameterException("Environment variables cannot be empty");
            }
            configuration.environmentVariables = environmentVariables;
            return this;
        }

        public Builder withDeadLetterConfig(String deadLetterTargetResourceArn) {
            Objects.requireNonNull(deadLetterTargetResourceArn, "Dead letter resource arn cannot be null");
            configuration.deadLetterConfig = Collections.singletonMap(DL_CONFIG_ARN, deadLetterTargetResourceArn);
            return this;
        }

        public Builder withTimeout(long timeout) {
            if (timeout <= 0) {
                throw new InvalidParameterException("Memory cannot be negative or 0");
            }
            configuration.timeoutInSec = timeout;
            return this;
        }


        public TerraformLambdaConfiguration build() {
            Objects.requireNonNull(configuration.functionName, "Function name cannot be null");
            Objects.requireNonNull(configuration.handler, "Function handler cannot be null");
            Objects.requireNonNull(configuration.roleArn, "Role arn cannot be null");
            Objects.requireNonNull(configuration.runtime, "Deployment runtime cannot be null");
            return this.configuration;
        }
    }

    public String getDeploymentPackageName() {
        return deploymentPackageName;
    }

    public String getFunctionName() {
        return functionName;
    }

    public String getHandler() {
        return handler;
    }

    public String getRoleArn() {
        return roleArn;
    }

    public long getMemorySize() {
        return memorySize;
    }

    public DeploymentRuntime getRuntime() {
        return runtime;
    }

    public boolean isPublishNewVersion() {
        return publishNewVersion;
    }

    public TerraformLambdaVpcConfig getVpcConfig() {
        return vpcConfig;
    }

    public Map<String, String> getEnvironmentVariables() {
        return environmentVariables;
    }
}
