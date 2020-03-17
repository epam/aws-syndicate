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

package com.syndicate.deployment.factories;

import com.syndicate.deployment.annotations.lambda.LambdaConcurrency;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.lambda.LambdaProvisionedConcurrency;
import com.syndicate.deployment.annotations.resources.DeadLetterConfiguration;
import com.syndicate.deployment.model.DependencyItem;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.ProvisionedConcurrency;
import com.syndicate.deployment.model.ResourceType;
import com.syndicate.deployment.model.TracingMode;
import com.syndicate.deployment.model.events.EventSourceItem;

import java.util.Map;
import java.util.Set;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
public final class LambdaConfigurationFactory {

    private static final String SEPARATOR = ":";

    private LambdaConfigurationFactory() {
    }

    public static LambdaConfiguration createLambdaConfiguration(String version, Class<?> lambdaClass,
                                                                LambdaHandler lambdaHandler, Set<DependencyItem> dependencies,
                                                                Set<EventSourceItem> events, Map<String, String> variables,
                                                                String packageName, String lambdaPath) {
        StringBuilder function = new StringBuilder(lambdaClass.getName());
        String methodName = lambdaHandler.methodName();
        if (!methodName.isEmpty()) {
            function.append(SEPARATOR).append(methodName);
        }
        LambdaConfiguration lambdaConfiguration = new LambdaConfiguration.Builder()
                .withPath(lambdaPath).withName(lambdaHandler.lambdaName())
                .withVersion(version).withRole(lambdaHandler.roleName()).withFunction(function.toString())
                .withRegionScope(lambdaHandler.regionScope()).withPackageName(packageName)
                .withMemory(lambdaHandler.memory()).withTimeout(lambdaHandler.timeout())
                .withRuntime(DeploymentRuntime.JAVA8).withResourceType(ResourceType.LAMBDA)
                .withDependencies(dependencies).withEventSources(events)
                .withVariables(variables).withSubnetIds(lambdaHandler.subnetsIds())
                .withSecurityGroupIds(lambdaHandler.securityGroupIds())
                .withPublishVersion(lambdaHandler.isPublishVersion())
                .build();

        if (lambdaHandler.tracingMode() != TracingMode.NoTracing) {
            lambdaConfiguration.setTracingMode(lambdaHandler.tracingMode().getMode());
        }

        String aliasName = lambdaHandler.aliasName();
        if (!aliasName.equals("")) {
            lambdaConfiguration.setAlias(aliasName);
        }

        String[] layers = lambdaHandler.layers();
        if (layers.length > 0) {
            lambdaConfiguration.setLayers(layers);
        }

        LambdaConcurrency lambdaConcurrency = lambdaClass.getDeclaredAnnotation(LambdaConcurrency.class);
        if (lambdaConcurrency != null) {
            lambdaConfiguration.setConcurrentExecutions(lambdaConcurrency.executions());
        }

        LambdaProvisionedConcurrency provisionedConcurrencyAnnotation = lambdaClass.getDeclaredAnnotation(LambdaProvisionedConcurrency.class);
        if (provisionedConcurrencyAnnotation != null) {
            ProvisionedConcurrency provisionedConcurrency = new ProvisionedConcurrency(
            	provisionedConcurrencyAnnotation.type(),
	            provisionedConcurrencyAnnotation.value());
            lambdaConfiguration.setProvisionedConcurrency(provisionedConcurrency);
        }

        DeadLetterConfiguration deadLetterConfiguration = lambdaClass.getDeclaredAnnotation(DeadLetterConfiguration.class);
        if (deadLetterConfiguration != null) {
            lambdaConfiguration.setDlResourceName(deadLetterConfiguration.resourceName());
            lambdaConfiguration.setDlResourceType(deadLetterConfiguration.resourceType().getServiceName());
        }

        return lambdaConfiguration;
    }

}
