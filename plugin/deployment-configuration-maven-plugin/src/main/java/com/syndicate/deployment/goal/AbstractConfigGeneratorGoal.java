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

import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.model.Pair;
import com.syndicate.deployment.model.api.request.SyndicateCredentials;
import com.syndicate.deployment.processor.IConfigurationProcessor;
import com.syndicate.deployment.resolvers.CredentialResolverChain;
import com.syndicate.deployment.resolvers.IChainedCredentialsResolver;
import com.syndicate.deployment.resolvers.impl.CliParametersCredentialResolver;
import com.syndicate.deployment.resolvers.impl.EnvironmentPropertiesCredentialsResolver;
import com.syndicate.deployment.utils.JsonUtils;
import com.syndicate.deployment.utils.ProjectUtils;
import org.apache.maven.artifact.DependencyResolutionRequiredException;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.logging.Log;
import org.apache.maven.plugins.annotations.Parameter;
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
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static com.syndicate.deployment.utils.ProjectUtils.SYNDICATE_BUILD_ID;
import static com.syndicate.deployment.utils.ProjectUtils.getPropertyFromRootProject;
import static com.syndicate.deployment.utils.ProjectUtils.getRootDirPath;
import static com.syndicate.deployment.utils.ProjectUtils.setPropertyToRootProject;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
public abstract class AbstractConfigGeneratorGoal<T> extends AbstractMojo {

	private static final String BUILD_FILE_EXT = ".sdctbuild";
	private static final String DEFAULT_ENCODING = "UTF-8";

    @Parameter(property = "maven.processor.credentials")
    private String credentials;

    @Parameter(defaultValue = "${project}", required = true, readonly = true)
    protected MavenProject project;

	@Parameter
	protected String url;

	@Parameter(required = true)
	private String fileName;

	@Parameter(property = "maven.processor.skip", defaultValue = "false")
	private boolean skip;

	@Parameter(property = "maven.processor.generateBuildFile", defaultValue = "false")
	private boolean generateBuildFile;

	@Parameter(required = true)
	private String[] packages;

	private CredentialResolverChain credentialsResolverChain;

	protected Log logger;


	public AbstractConfigGeneratorGoal() {
		this.logger = getLog();

		IChainedCredentialsResolver cliParamCredentialResolver = new CliParametersCredentialResolver(credentials);
		IChainedCredentialsResolver environmentVarsCredentialsResolver = new EnvironmentPropertiesCredentialsResolver();
		cliParamCredentialResolver.setNextResolver(environmentVarsCredentialsResolver);

		this.credentialsResolverChain = new CredentialResolverChain(cliParamCredentialResolver);
	}

	public MavenProject getProject() {
		return project;
	}

	public void setProject(MavenProject project) {
		this.project = project;
	}

	public boolean isSkip() {
		return skip;
	}

	public void setSkip(boolean skip) {
		this.skip = skip;
	}

	public String[] getPackages() {
		return packages;
	}

	public void setPackages(String[] packages) {
		this.packages = packages;
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

    @Override
    public void execute() throws MojoExecutionException {
        if (skip) {
            logger.info("lambda-configuration-processor is skipped");
            return;
        }
        logger.info("Start creating resources_config.json ...");
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

            Map<String, T> configurations = new HashMap<>();
            for (Class<?> lambdaClass: lambdasClasses) {
                IConfigurationProcessor<T> annotationProcessor =
                        getAnnotationProcessor(project.getVersion(), fileName, absolutePath, lambdaClass);
                Pair<String, T> lambdaConfigurationPair = annotationProcessor.process();

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

            Map<String, Object> convertedConfiguration = convertConfiguration(configurations);
            writeToFile(ProjectUtils.getTargetFolderPath(project), getDeploymentResourcesFileName(), JsonUtils.convertToJson(convertedConfiguration));

			// credentials are set up, using Syndicate API to upload meta information
			SyndicateCredentials userCredentials = credentialsResolverChain.resolveCredentialsInChain();
			if (userCredentials != null) {
				generateBuildId();
				uploadMeta(convertedConfiguration, userCredentials);
			}

        } catch (IOException e) {
            throw new MojoExecutionException("Goal execution failed", e);
        }
    }

    protected abstract Map<String, Object> convertConfiguration(Map<String, T> configurations);

    public abstract String getDeploymentResourcesFileName();

    public abstract IConfigurationProcessor<T> getAnnotationProcessor(
            String version, String fileName, String absolutePath, Class<?> lambdaClass);

	public abstract void uploadMeta(Map<String, Object> configurations, SyndicateCredentials credentials);

    private Set<URI> getUris() throws MojoExecutionException {
        Set<URI> uris = new HashSet<>();
        try {
            // getting classpath of the current module
            List<String> elements = project.getCompileClasspathElements();
            // getting uris of the dependencies to inject into classloader
            // url presents file location of the dependency in the module
            for (String element: elements) {
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
        for (String nestedPackage: packages) {
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

	private void generateBuildId() {
		if (getPropertyFromRootProject(project, SYNDICATE_BUILD_ID) != null) {
			return;
		}
		String generatedBuildId = UUID.randomUUID().toString();
		logger.info("Newly generated build id: " + generatedBuildId);
		setPropertyToRootProject(project, SYNDICATE_BUILD_ID, generatedBuildId);
		if (generateBuildFile) {
			try {
				String rootDirPath = getRootDirPath(project);
				String sdctBuildFileName = generatedBuildId + BUILD_FILE_EXT;
				String filePathName = rootDirPath + '/' + sdctBuildFileName;
				// never overrides the file due to check at the method beginning
				writeToFile(rootDirPath, sdctBuildFileName,
					JsonUtils.convertToJson(Collections.singletonMap("buildId", generatedBuildId)));
				logger.debug(filePathName + " file successfully created");
			} catch (IOException e) {
				logger.error("Failed to write " + BUILD_FILE_EXT, e);
				throw new RuntimeException("Failed to write " + BUILD_FILE_EXT, e);
			}
		}
	}

}
