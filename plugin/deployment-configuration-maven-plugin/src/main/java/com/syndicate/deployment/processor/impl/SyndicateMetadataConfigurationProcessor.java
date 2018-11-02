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
package com.syndicate.deployment.processor.impl;

import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.factories.LambdaConfigurationFactory;
import com.syndicate.deployment.model.DependencyItem;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.events.EventSourceItem;
import com.syndicate.deployment.processor.ConfigurationMetadataAnnotationProcessor;

import java.util.Map;
import java.util.Set;

/**
 * Created by Oleksandr Onsha on 10/25/18
 */
public class SyndicateMetadataConfigurationProcessor extends ConfigurationMetadataAnnotationProcessor<LambdaConfiguration> {

    public SyndicateMetadataConfigurationProcessor(String version, Class<?> lambdaClass, String fileName, String lambdaPath) {
        super(version, lambdaClass, fileName, lambdaPath);
    }

    @Override
    protected LambdaConfiguration createLambdaConfiguration(
            String version, Class<?> lambdaClass, LambdaHandler lambdaHandler, Set<DependencyItem> dependencies,
            Set<EventSourceItem> events, Map<String, String> variables, String packageName, String lambdaPath) {
        return LambdaConfigurationFactory.createLambdaConfiguration(version,
                lambdaClass, lambdaHandler, dependencies, events, variables, packageName, lambdaPath);
    }
}
