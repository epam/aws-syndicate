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
package com.syndicate.deployment.goal;

import com.syndicate.deployment.api.clients.SyndicateEnterpriseClient;
import com.syndicate.deployment.api.model.request.SaveMetaRequest;
import com.syndicate.deployment.api.model.request.SyndicateCredentials;
import com.syndicate.deployment.api.model.response.SaveMetaResponse;
import com.syndicate.deployment.api.model.response.TokenResponse;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.LayerConfiguration;
import com.syndicate.deployment.processor.IAnnotationProcessor;
import com.syndicate.deployment.processor.impl.LambdaHandlerAnnotationProcessor;
import com.syndicate.deployment.processor.impl.LayerAnnotationProcessor;
import com.syndicate.deployment.resolvers.credentials.CredentialResolverChain;
import com.syndicate.deployment.resolvers.credentials.IChainedCredentialsResolver;
import com.syndicate.deployment.resolvers.credentials.impl.CliParametersCredentialResolver;
import com.syndicate.deployment.resolvers.credentials.impl.EnvironmentPropertiesCredentialsResolver;
import com.syndicate.deployment.utils.JsonUtils;
import com.syndicate.deployment.utils.ProjectUtils;
import feign.Feign;
import feign.jackson.JacksonDecoder;
import feign.jackson.JacksonEncoder;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;

import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static com.syndicate.deployment.utils.ProjectUtils.SYNDICATE_BUILD_ID;
import static com.syndicate.deployment.utils.ProjectUtils.getPropertyFromRootProject;
import static com.syndicate.deployment.utils.ProjectUtils.getRootDirPath;
import static com.syndicate.deployment.utils.ProjectUtils.setPropertyToRootProject;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
@Mojo(name = "gen-deployment-config", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class SyndicateMetaGeneratorGoal extends AbstractMetaGoal {

    private static final String BUILD_FILE_EXT = ".sdctbuild";


    private static final String DEPLOYMENT_RESOURCES_JSON_FILE_NAME = "deployment_resources.json";

    @Parameter
    private String url;

    @Parameter(property = "maven.processor.credentials")
    private String credentials;

    @Parameter(property = "maven.processor.generateBuildFile", defaultValue = "false")
    private boolean generateBuildFile;

    @Parameter(property = "maven.processor.buildId")
    private String buildId;

    private CredentialResolverChain credentialsResolverChain;

    private IAnnotationProcessor<LambdaConfiguration> lambdaAnnotationProcessor;
    private IAnnotationProcessor<LayerConfiguration> layerAnnotationProcessor;


    public SyndicateMetaGeneratorGoal() {
        lambdaAnnotationProcessor = new LambdaHandlerAnnotationProcessor();
        layerAnnotationProcessor = new LayerAnnotationProcessor();

        IChainedCredentialsResolver cliParamCredentialResolver = new CliParametersCredentialResolver(credentials);
        IChainedCredentialsResolver environmentVarsCredentialsResolver = new EnvironmentPropertiesCredentialsResolver();
        cliParamCredentialResolver.setNextResolver(environmentVarsCredentialsResolver);

        this.credentialsResolverChain = new CredentialResolverChain(cliParamCredentialResolver);
    }

    @Override
    public void executeGoal(String absolutePath) throws MojoExecutionException, IOException {
        Map<String, LambdaConfiguration> lambdaConfiguration =
                lambdaAnnotationProcessor.generateMeta(absolutePath, packages, project.getVersion(), this.fileName);
        Map<String, LayerConfiguration> layerConfiguration =
                layerAnnotationProcessor.generateMeta(absolutePath, packages, project.getVersion(), fileName);

        Map<String, Object> convertedMeta = convertConfiguration(lambdaConfiguration, layerConfiguration);
        writeToFile(ProjectUtils.getTargetFolderPath(project), getDeploymentResourcesFileName(), JsonUtils.convertToJson(convertedMeta));

        // credentials are set up, using Syndicate API to upload meta information
        SyndicateCredentials userCredentials = credentialsResolverChain.resolveCredentialsInChain();
        if (userCredentials != null) {
            generateBuildId();
            uploadMeta(convertedMeta, userCredentials);
        }
    }

    protected String getDeploymentResourcesFileName() {
        return DEPLOYMENT_RESOURCES_JSON_FILE_NAME;
    }

    protected Map<String, Object> convertConfiguration(Map<String, LambdaConfiguration> lambdaConfiguration,
                                                       Map<String, LayerConfiguration> layerConfiguration) {
        Map<String, Object> convertedMeta = new HashMap<>();
        convertedMeta.putAll(lambdaAnnotationProcessor.convertMeta(lambdaConfiguration));
        convertedMeta.putAll(layerAnnotationProcessor.convertMeta(layerConfiguration));
        return convertedMeta;
    }


    protected void uploadMeta(Map<String, Object> configurations, SyndicateCredentials credentials) {
        String buildId = ProjectUtils.getPropertyFromRootProject(project, SYNDICATE_BUILD_ID);

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

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public CredentialResolverChain getCredentialsResolverChain() {
        return credentialsResolverChain;
    }

    public void setCredentialsResolverChain(CredentialResolverChain credentialsResolverChain) {
        this.credentialsResolverChain = credentialsResolverChain;
    }

    private void generateBuildId() {
        if (getPropertyFromRootProject(project, SYNDICATE_BUILD_ID) != null) {
            return;
        }
        String buildId = this.buildId;
        if (buildId == null) {
            buildId = UUID.randomUUID().toString();
            logger.info("Newly generated build id: " + buildId);
        }
        setPropertyToRootProject(project, SYNDICATE_BUILD_ID, buildId);
        if (generateBuildFile) {
            try {
                String rootDirPath = getRootDirPath(project);
                String sdctBuildFileName = buildId + BUILD_FILE_EXT;
                String filePathName = rootDirPath + '/' + sdctBuildFileName;
                // never overrides the file due to check at the method beginning
                writeToFile(rootDirPath, sdctBuildFileName,
                        JsonUtils.convertToJson(Collections.singletonMap("buildId", buildId)));
                logger.debug(filePathName + " file successfully created");
            } catch (IOException e) {
                logger.error("Failed to write " + BUILD_FILE_EXT, e);
                throw new RuntimeException("Failed to write " + BUILD_FILE_EXT, e);
            }
        }
    }
}