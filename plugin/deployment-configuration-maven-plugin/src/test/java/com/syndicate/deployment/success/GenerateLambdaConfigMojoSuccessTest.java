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

package com.syndicate.deployment.success;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.syndicate.deployment.goal.SyndicateMetaGeneratorGoal;
import com.syndicate.deployment.goal.TerraformMetaGeneratorGoal;
import com.syndicate.deployment.model.*;
import com.syndicate.deployment.model.events.SnsTriggerEventSourceItem;
import com.syndicate.deployment.model.terraform.TerraformLambdaConfiguration;
import com.syndicate.deployment.resolvers.credentials.CredentialResolverChain;
import com.syndicate.deployment.success.syndicate.SnsLambdaExecutor;
import com.syndicate.deployment.success.syndicate.SnsLambdaProcessor;
import com.syndicate.deployment.success.terraform.BackgroundLambda;
import com.syndicate.deployment.success.terraform.ForegroundLambda;
import org.apache.maven.model.Build;
import org.apache.maven.plugin.testing.MojoRule;
import org.apache.maven.project.MavenProject;
import org.junit.Assert;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.PrintStream;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Created by Vladyslav Tereshchenko on 8/30/2018.
 */
public class GenerateLambdaConfigMojoSuccessTest {

    public static final String PLUGIN_ARTIFACT_ID = "deployment-configuration-maven-plugin";
    private static final String PLUGIN_CONFIG_SKIP_XML = "plugin-config-skip.xml";
    private static final Properties EMPTY_PROPERTIES = new Properties();

    private ObjectMapper objectMapper = new ObjectMapper();

    @Rule
    public MojoRule rule = new MojoRule();

    @Rule
    public TemporaryFolder folder = new TemporaryFolder(new File("."));

    @Test
    public void testMojoExists() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource(PLUGIN_CONFIG_SKIP_XML)).toURI());

        SyndicateMetaGeneratorGoal mojo = new SyndicateMetaGeneratorGoal();
        mojo = (SyndicateMetaGeneratorGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));
        Assert.assertNotNull(mojo);
    }

    @Test
    public void testPluginSkipped() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource(PLUGIN_CONFIG_SKIP_XML)).toURI());

        SyndicateMetaGeneratorGoal mojo = new SyndicateMetaGeneratorGoal();
        mojo = (SyndicateMetaGeneratorGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));

        // need to test output in the console
        ByteArrayOutputStream outStream = new ByteArrayOutputStream();
        PrintStream testConsole = new PrintStream(outStream);
        PrintStream trueConsole = System.out;

        System.setOut(testConsole);
        mojo.execute();
        System.setOut(trueConsole);

        assertEquals("[info] lambda-configuration-processor is skipped", outStream.toString().trim().toLowerCase());
    }

    @Test
    public void testPackagesPassed() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource(PLUGIN_CONFIG_SKIP_XML)).toURI());

        SyndicateMetaGeneratorGoal mojo = new SyndicateMetaGeneratorGoal();
        mojo = (SyndicateMetaGeneratorGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));

        assertArrayEquals(new String[]{"com.syndicate"}, mojo.getPackages());
    }

    @Test
    public void testSyndicateGoalExecuted() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource("plugin-config-syndicate-goal.xml")).toURI());

        SyndicateMetaGeneratorGoal mojo = new SyndicateMetaGeneratorGoal();
        mojo = (SyndicateMetaGeneratorGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));

        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getCompileClasspathElements()).thenReturn(Arrays.asList("dep1", "dep2"));
        final Build build = mock(Build.class);
        final File file = mock(File.class);
        when(mavenProject.getParent()).thenReturn(mavenProject);
        when(mavenProject.getBuild()).thenReturn(build);
        when(mavenProject.getBuild().getFinalName()).thenReturn("syndicate");
        when(mavenProject.getVersion()).thenReturn("1.0.0");
        when(mavenProject.getBasedir()).thenReturn(file);
        when(mavenProject.getProperties()).thenReturn(EMPTY_PROPERTIES);

        File targetDir = folder.newFolder("target");
        when(mavenProject.getBasedir().getAbsolutePath()).thenReturn(folder.getRoot().getAbsolutePath());

        mojo.setProject(mavenProject);
        // override packages to process only current class file
        mojo.setPackages(new String[]{"com.syndicate.deployment.success.syndicate"});
        mojo.setFileName("syndicate.jar");
        mojo.setCredentialsResolverChain(new CredentialResolverChain(null));
        mojo.execute();

        // will be created 1 file with lambdas description
        File[] files = targetDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".json"));
        if (files == null) {
            files = new File[]{};
        }

        assertEquals(1, files.length);

        // configs are equal
        // lambda_execute_notification
        LambdaConfiguration snsLambdaExecutorConfiguration = new LambdaConfiguration.Builder()
                .withName("lambda_execute_notification")
                .withTracingMode(TracingMode.Active.getMode())
                .withMemory(1024)
                .withFunction(SnsLambdaExecutor.class.getName())
                .withPackageName("syndicate.jar")
                .withPath(folder.getRoot().getAbsolutePath())
                .withRole("lr_get_notification_content")
                .withRuntime(DeploymentRuntime.JAVA8)
                .withVersion("1.0.0")
                .withTimeout(300)
                .withDependencies(Collections.singleton(new DependencyItem.Builder()
                        .withResourceName("stackAuditTopic")
                        .withResourceType(ResourceType.SNS_TOPIC)
                        .build()))
                .withEventSources(Collections.singleton(new SnsTriggerEventSourceItem.Builder()
                        .withTargetTopic("stackAuditTopic")
                        .withRegionScope(RegionScope.ALL)
                        .build()))
                .withVariables(Collections.singletonMap("name", "lambda_execute_notification"))
                .withSubnetIds(new String[]{})
                .withSecurityGroupIds(new String[]{})
                .withResourceType(ResourceType.LAMBDA)
                .withSnapStart(LambdaSnapStart.PublishedVersions)
                .build();

        // lambda_process_notification
        LambdaConfiguration snsLambdaProcessorConfiguration = new LambdaConfiguration.Builder()
                .withName("lambda_process_notification")
                .withTracingMode(TracingMode.Active.getMode())
                .withMemory(1024)
                .withFunction(SnsLambdaProcessor.class.getName() + ":handle")
                .withPackageName("syndicate.jar")
                .withPath(folder.getRoot().getAbsolutePath())
                .withRole("lr_get_notification_content")
                .withRuntime(DeploymentRuntime.JAVA8)
                .withVersion("1.0.0")
                .withTimeout(300)
                .withDependencies(Collections.singleton(new DependencyItem.Builder()
                        .withResourceName("stackAuditTopic")
                        .withResourceType(ResourceType.SNS_TOPIC)
                        .build()))
                .withEventSources(Collections.singleton(new SnsTriggerEventSourceItem.Builder()
                        .withTargetTopic("stackAuditTopic")
                        .withRegionScope(RegionScope.ALL)
                        .build()))
                .withVariables(Collections.singletonMap("name", "lambda_process_notification"))
                .withSubnetIds(new String[]{})
                .withSecurityGroupIds(new String[]{})
                .withResourceType(ResourceType.LAMBDA)
                .withConcurrentExecutions(1)
                .withDlResourceName("lambda-dead-letter-queue-name")
                .withDlResourceType("sqs")
                .withSnapStart(LambdaSnapStart.None)
                .build();


        File deploymentResourcesFile = Arrays.stream(files).filter(f -> f.getName()
                .equalsIgnoreCase("deployment_resources.json"))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("There no files names as deployment_resource.json"));

        String deploymentResourcesJson = new String(Files.readAllBytes(deploymentResourcesFile.toPath()));
        Map<String, JsonNode> actualContent = objectMapper.readValue(deploymentResourcesJson,
                new TypeReference<Map<String, JsonNode>>() {
                });
        Map<String, JsonNode> expectedContent = new HashMap<>();
        expectedContent.put("lambda_process_notification", objectMapper.readTree(
                objectMapper.writeValueAsString(snsLambdaProcessorConfiguration)));
        expectedContent.put("lambda_execute_notification", objectMapper.readTree(
                objectMapper.writeValueAsString(snsLambdaExecutorConfiguration)));
        assertEquals(expectedContent, actualContent);
    }

    @Test
    public void testTerraformGoalExecuted() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource("plugin-config-terraform-goal.xml")).toURI());

        TerraformMetaGeneratorGoal mojo = new TerraformMetaGeneratorGoal();
        mojo = (TerraformMetaGeneratorGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));
        //Set properties directly into mojo due to non-existing ability lo extract goal configuration from xml
        mojo.setRegion("us-east-1");
        mojo.setAccountId("012345678901");

        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getParent()).thenReturn(mavenProject);
        when(mavenProject.getCompileClasspathElements()).thenReturn(Arrays.asList("dep1", "dep2"));
        final Build build = mock(Build.class);
        final File file = mock(File.class);
        when(mavenProject.getBuild()).thenReturn(build);

        when(mavenProject.getBuild().getFinalName()).thenReturn("terraform");
        when(mavenProject.getVersion()).thenReturn("1.0.0");
        when(mavenProject.getBasedir()).thenReturn(file);
        when(mavenProject.getProperties()).thenReturn(EMPTY_PROPERTIES);

        File targetDir = folder.newFolder("target");
        when(mavenProject.getBasedir().getAbsolutePath()).thenReturn(folder.getRoot().getAbsolutePath());

        mojo.setProject(mavenProject);
        // override packages to process only current class file
        mojo.setPackages(new String[]{"com.syndicate.deployment.success.terraform"});
        mojo.setFileName("terraform.jar");
        mojo.setCredentialsResolverChain(new CredentialResolverChain(null));
        mojo.execute();
        // will be created 1 file with lambdas description
        File[] files = targetDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".json"));
        if (files == null) {
            files = new File[]{};
        }

        assertEquals(1, files.length);

        TerraformLambdaConfiguration foregroundLambdaConfiguration = new TerraformLambdaConfiguration.Builder()
                .withMemorySize(1024)
                .withFunctionName("foreground_lambda")
                .withDeploymentPackageName(folder.getRoot().getAbsolutePath() + "/target/terraform.jar")
                .withRuntime(DeploymentRuntime.JAVA8)
                .withHandler(ForegroundLambda.class.getName())
                .withRole("arn:aws:iam::012345678901:role/foreground-lambda-role")
                .withTimeout(300)
                .withEnvironmentVariables(Collections.singletonMap("name", "foreground_lambda"))
                .build();

        TerraformLambdaConfiguration backgroundLambdaConfiguration = new TerraformLambdaConfiguration.Builder()
                .withMemorySize(1024)
                .withFunctionName("background_lambda")
                .withDeploymentPackageName(folder.getRoot().getAbsolutePath() + "/target/terraform.jar")
                .withRuntime(DeploymentRuntime.JAVA8)
                .withHandler(BackgroundLambda.class.getName() + ":handle")
                .withRole("arn:aws:iam::012345678901:role/background-lambda-role")
                .withTimeout(300)
                .withEnvironmentVariables(Collections.singletonMap("name", "background_lambda"))
                .withDeadLetterConfig("arn:aws:sqs:us-east-1:012345678901:lambda-dead-letter-queue-name")
                .build();


        File deploymentResourcesFile = Arrays.stream(files).filter(f -> f.getName()
                .equalsIgnoreCase("deployment_resources.tf.json"))
                .findFirst()
	            .orElseThrow(() -> new IllegalArgumentException("There no files names as deployment_resource.tf.json"));


        String deploymentResourcesJson = new String(Files.readAllBytes(deploymentResourcesFile.toPath()));
        Map<String, JsonNode> actualContent = objectMapper.readValue(deploymentResourcesJson,
                new TypeReference<Map<String, JsonNode>>() {
                });

        Map<String, JsonNode> expectedContent = new HashMap<>();
        Map<String, TerraformLambdaConfiguration> lambda_resources = new HashMap<>();

        lambda_resources.put("foreground_lambda", foregroundLambdaConfiguration);
        lambda_resources.put("background_lambda", backgroundLambdaConfiguration);
        expectedContent.put("resource", objectMapper.readTree(
                objectMapper.writeValueAsString(
                        Collections.singletonMap("aws_lambda_function", lambda_resources)
                )));

        Map<String, Object> provider = Collections.singletonMap("aws",
                Collections.singletonMap("region", "us-east-1"));
        expectedContent.put("provider", objectMapper.readTree(
                objectMapper.writeValueAsString(provider)));
        assertEquals(expectedContent, actualContent);
    }

}