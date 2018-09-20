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

package com.syndicate.deployment;

import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.processor.IConfigurationProcessor;
import com.syndicate.deployment.processor.impl.ConfigurationMetadataAnnotationProcessor;
import com.syndicate.deployment.utils.JsonUtils;
import javafx.util.Pair;
import org.apache.maven.artifact.DependencyResolutionRequiredException;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugin.logging.Log;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;
import org.apache.maven.project.MavenProject;
import org.reflections.Reflections;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.UnsupportedEncodingException;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
@Mojo(name = "gen-deployment-config", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class GenerateLambdaConfigGoal extends AbstractMojo {

    private static final String EXTENSION_JAR = ".jar";
    private static final String MAVEN_TARGET_FOLDER_NAME = "target";
    private static final String DEFAULT_ENCODING = "UTF-8";
    private static final String DEPLOYMENT_RESOURCES_JSON_FILE_NAME = "deployment_resources.json";

    @Parameter(defaultValue = "${project}", required = true, readonly = true)
    private MavenProject project;

    @Parameter(property = "maven.processor.skip", defaultValue = "false")
    private boolean skip;

    @Parameter(required = true)
    private String[] packages;

    private Log logger;

    public GenerateLambdaConfigGoal() {
        this.logger = getLog();
    }

    public void setProject(MavenProject project) {
        this.project = project;
    }

    public void setSkip(boolean skip) {
        this.skip = skip;
    }

    public void setPackages(String[] packages) {
        this.packages = packages;
    }

    public MavenProject getProject() {
        return project;
    }

    public boolean isSkip() {
        return skip;
    }

    public String[] getPackages() {
        return packages;
    }

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            logger.info("lambda-configuration-processor is skipped");
            return;
        }
        logger.info("Start creating resources_config.json ...");
        String fileName = project.getBuild().getFinalName() + EXTENSION_JAR;
        logger.info("Path to deployment package ==> " + fileName);

        logger.debug("Creating custom classpath ...");

        Set<URI> uris = getUris();
        // creating custom classloader with specified module dependencies
        URL[] urlArray = getUrls(uris);
        try (URLClassLoader contextClassLoader = URLClassLoader.newInstance(urlArray,
                Thread.currentThread().getContextClassLoader())) {
            // setting up created classpath as a current classloader
            Thread.currentThread().setContextClassLoader(contextClassLoader);

            String absolutePath = project.getBasedir().getAbsolutePath();
            Set<String> uniqueLambdaNames = new HashSet<>();
            List<Class<?>> lambdasClasses = getLambdaClasses();

            Map<String, LambdaConfiguration> configurations = new HashMap<>();
            for (Class<?> lambdaClass : lambdasClasses) {
                IConfigurationProcessor<LambdaConfiguration> annotationProcessor =
                        new ConfigurationMetadataAnnotationProcessor(project.getVersion(), lambdaClass,
                                fileName, absolutePath);
                Pair<String, LambdaConfiguration> lambdaConfigurationPair = annotationProcessor.process();

                String lambdaName = lambdaConfigurationPair.getKey();
                logger.info("Lambda name: " + lambdaName);

                if (uniqueLambdaNames.contains(lambdaName)) {
                    throw new MojoExecutionException("Find more than one lambda with name : "
                            + lambdaName + "! Lambda name must be unique.");
                } else {
                    uniqueLambdaNames.add(lambdaName);
                }

                logger.info("Lambda configuration is created");
                if (configurations.containsKey(lambdaName)) {
                    throw new MojoExecutionException("Configuration " + lambdaName + " is duplicated.");
                }
                configurations.put(lambdaName, lambdaConfigurationPair.getValue());
                logger.info("Goal executed successfully");
            }

            String configPath = absolutePath + File.separator + MAVEN_TARGET_FOLDER_NAME;
            // write found configurations to meta file
            writeToFile(configPath, DEPLOYMENT_RESOURCES_JSON_FILE_NAME, JsonUtils.convertToJson(configurations));

        } catch (IOException e) {
            throw new MojoExecutionException("Goal execution failed", e);
        }
    }

    private Set<URI> getUris() throws MojoExecutionException {
        Set<URI> uris = new HashSet<>();
        try {
            // getting classpath of the current module
            List<String> elements = project.getCompileClasspathElements();
            // getting uris of the dependencies to inject into classloader
            // url presents file location of the dependency in the module
            for (String element : elements) {
                uris.add(new File(element).toURI());
            }
            logger.debug("Setting up new classloader ...");

        } catch (DependencyResolutionRequiredException e) {
            throw new MojoExecutionException("Dependency does not exist", e);
        }
        return uris;
    }

    private URL[] getUrls(Set<URI> uris) {
        return uris.stream()
                .map(uri -> {
                    try {
                        return uri.toURL();
                    } catch (MalformedURLException e) {
                        logger.error("Illegal protocol to URI. " + e.getMessage());
                        return null;
                    }
                }).toArray(URL[]::new);
    }

    private List<Class<?>> getLambdaClasses() {
        List<Class<?>> lambdasClasses = new ArrayList<>();
        for (String nestedPackage : packages) {
            lambdasClasses.addAll(new Reflections(nestedPackage).getTypesAnnotatedWith(LambdaHandler.class));
        }
        return lambdasClasses;
    }

    private void writeToFile(String folderPath, String fileName, String content) throws IOException {
        String filePath = folderPath + File.separator + fileName;
        try (PrintWriter printWriter = new PrintWriter(filePath, DEFAULT_ENCODING)) {
            printWriter.write(content);
        } catch (FileNotFoundException e) {
            throw new IOException("Cannot find file. Path ==> " + folderPath, e);
        } catch (UnsupportedEncodingException e) {
            throw new IOException("Incorrect encoding ==> " + DEFAULT_ENCODING, e);
        }
    }

}
