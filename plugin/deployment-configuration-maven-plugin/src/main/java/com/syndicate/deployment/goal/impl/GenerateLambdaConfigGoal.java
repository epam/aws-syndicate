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

package com.syndicate.deployment.goal.impl;

import com.syndicate.deployment.goal.AbstractConfigGeneratorGoal;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.processor.impl.SyndicateMetadataConfigurationProcessor;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.ResolutionScope;

import java.util.Map;
import java.util.stream.Collectors;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
@Mojo(name = "gen-deployment-config", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class GenerateLambdaConfigGoal extends AbstractConfigGeneratorGoal<LambdaConfiguration> {

    private static final String DEPLOYMENT_RESOURCES_JSON_FILE_NAME = "deployment_resources.json";

    @Override
    protected Map<String, Object> convertConfiguration(Map<String, LambdaConfiguration> configurations) {
        return configurations.entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, e -> (Object) e.getValue()));
    }

    @Override
    public String getDeploymentResourcesFileName() {
        return DEPLOYMENT_RESOURCES_JSON_FILE_NAME;
    }

    public SyndicateMetadataConfigurationProcessor getAnnotationProcessor(String version, String fileName,
                                                                          String absolutePath, Class<?> lambdaClass) {
        return new SyndicateMetadataConfigurationProcessor(version, lambdaClass, fileName, absolutePath);
    }

}