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

import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.events.DynamoDbTriggerEventSource;
import com.syndicate.deployment.annotations.events.RuleEventSource;
import com.syndicate.deployment.annotations.events.S3EventSource;
import com.syndicate.deployment.annotations.events.SnsEventSource;
import com.syndicate.deployment.annotations.events.SqsTriggerEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.factories.DependencyItemFactory;
import com.syndicate.deployment.factories.LambdaConfigurationFactory;
import com.syndicate.deployment.model.DependencyItem;
import com.syndicate.deployment.model.EventSourceType;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.events.EventSourceItem;
import com.syndicate.deployment.processor.IConfigurationProcessor;
import javafx.util.Pair;

import java.lang.annotation.Annotation;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
public class ConfigurationMetadataAnnotationProcessor implements IConfigurationProcessor<LambdaConfiguration> {

    private static final Map<Class, EventSourceType> ANNOTATIONS = new HashMap<>();

    private final String version;

    private final Class<?> lambdaClass;

    private final String fileName;

    private final String lambdaPath;

    static {
        ANNOTATIONS.put(DynamoDbTriggerEventSource.class, EventSourceType.DYNAMODB_TRIGGER);
        ANNOTATIONS.put(RuleEventSource.class, EventSourceType.CLOUDWATCH_RULE_TRIGGER);
        ANNOTATIONS.put(S3EventSource.class, EventSourceType.S3_TRIGGER);
        ANNOTATIONS.put(SnsEventSource.class, EventSourceType.SNS_TOPIC_TRIGGER);
        ANNOTATIONS.put(SqsTriggerEventSource.class, EventSourceType.SQS_TRIGGER);
    }

    public ConfigurationMetadataAnnotationProcessor(String version, Class<?> lambdaClass,
                                                    String fileName, String lambdaPath) {
        this.version = version;
        this.lambdaClass = lambdaClass;
        this.fileName = fileName;
        this.lambdaPath = lambdaPath;
    }

    @Override
    public Pair<String, LambdaConfiguration> process() {
        LambdaHandler lambdaHandler = lambdaClass.getAnnotation(LambdaHandler.class);
        Set<EventSourceItem> events = new HashSet<>();
        Set<DependencyItem> dependencies = new HashSet<>();
        for (Map.Entry<Class, EventSourceType> annotationEntry : ANNOTATIONS.entrySet()) {
            Annotation[] annotations = lambdaClass.getDeclaredAnnotationsByType(annotationEntry.getKey());
            for (Annotation eventSource : annotations) {
                EventSourceType eventSourceType = annotationEntry.getValue();
                events.add(eventSourceType.createEventSourceItem(eventSource));
                // auto-processing dependencies for event sources
                dependencies.add(eventSourceType.createDependencyItem(eventSource));
            }
        }
        // process additional resources such as tables, another buckets etc
        DependsOn[] dependsOnAnnotations = lambdaClass.getDeclaredAnnotationsByType(DependsOn.class);
        for (DependsOn annotation : dependsOnAnnotations) {
            dependencies.add(DependencyItemFactory.createDependencyItem(annotation));
        }
        Map<String, String> envVariables = getEnvVariables();
        LambdaConfiguration lambdaConfiguration = LambdaConfigurationFactory.createLambdaConfiguration(version,
                lambdaClass, lambdaHandler, dependencies, events, envVariables, fileName, lambdaPath);
        return new Pair<>(lambdaHandler.lambdaName(), lambdaConfiguration);
    }

    private Map<String, String> getEnvVariables() {
        Map<String, String> envVariables = new HashMap<>();
        EnvironmentVariable[] environmentVariablesAnnotations = lambdaClass.getDeclaredAnnotationsByType(EnvironmentVariable.class);
        for (EnvironmentVariable annotation : environmentVariablesAnnotations) {
            envVariables.put(annotation.key(), annotation.value());
        }
        return envVariables;
    }

}
