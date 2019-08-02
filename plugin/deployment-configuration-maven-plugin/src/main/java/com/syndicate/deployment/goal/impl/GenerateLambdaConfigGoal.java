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

import com.syndicate.deployment.clients.SyndicateEnterpriseClient;
import com.syndicate.deployment.goal.AbstractConfigGeneratorGoal;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.api.request.Credentials;
import com.syndicate.deployment.model.api.request.SaveMetaRequest;
import com.syndicate.deployment.model.api.response.SaveMetaResponse;
import com.syndicate.deployment.model.api.response.TokenResponse;
import com.syndicate.deployment.processor.impl.SyndicateMetadataConfigurationProcessor;
import feign.Feign;
import feign.jackson.JacksonDecoder;
import feign.jackson.JacksonEncoder;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.ResolutionScope;
import org.apache.maven.project.MavenProject;

import java.security.InvalidParameterException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Map;
import java.util.Objects;
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

    @Override
    public void uploadMeta(Map<String, Object> configurations, Credentials credentials) {
        String buildId;
        // extract build id from root project
        // find root project
        MavenProject root = project.getParent();
        if (root != null) {
            while (root.getParent() != null) {
                root = root.getParent();
            }
            buildId = root.getProperties().get("syndicate-build-id").toString();
        } else {
            // root project is a lambda function
            buildId = project.getProperties().get("syndicate-build-id").toString();
        }

        SyndicateEnterpriseClient syndicateEnterpriseClient = Feign.builder()
                .encoder(new JacksonEncoder())
                .decoder(new JacksonDecoder())
                .target(SyndicateEnterpriseClient.class, url);

        TokenResponse tokenResponse = syndicateEnterpriseClient.token(credentials);
        String token = tokenResponse.getToken();

        SaveMetaRequest saveMetaRequest = new SaveMetaRequest(buildId, Instant.now().toEpochMilli(),
                new ArrayList<>(configurations.values()));

        SaveMetaResponse saveMetaResponse = syndicateEnterpriseClient.saveMeta(token, saveMetaRequest);
        logger.info(saveMetaResponse.getMessage());
        logger.info("Build id: " + saveMetaResponse.getBuildId());
    }

}