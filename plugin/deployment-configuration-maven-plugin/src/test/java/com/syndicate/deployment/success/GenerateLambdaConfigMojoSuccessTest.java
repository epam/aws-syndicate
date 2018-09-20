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
import com.syndicate.deployment.GenerateLambdaConfigGoal;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.events.SnsEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaConcurrency;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DeadLetterConfiguration;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.model.DeadLetterResourceType;
import com.syndicate.deployment.model.DependencyItem;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.LambdaConfiguration;
import com.syndicate.deployment.model.RegionScope;
import com.syndicate.deployment.model.ResourceType;
import com.syndicate.deployment.model.TracingMode;
import com.syndicate.deployment.model.events.SnsTriggerEventSourceItem;
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

    private ObjectMapper objectMapper = new ObjectMapper();

    @Rule
    public MojoRule rule = new MojoRule();

    @Rule
    public TemporaryFolder folder = new TemporaryFolder(new File("."));

    @Test
    public void testMojoExists() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource(PLUGIN_CONFIG_SKIP_XML)).getFile());

        GenerateLambdaConfigGoal mojo = new GenerateLambdaConfigGoal();
        mojo = (GenerateLambdaConfigGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));
        Assert.assertNotNull(mojo);
    }

    @Test
    public void testPluginSkipped() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource(PLUGIN_CONFIG_SKIP_XML)).getFile());

        GenerateLambdaConfigGoal mojo = new GenerateLambdaConfigGoal();
        mojo = (GenerateLambdaConfigGoal) rule.configureMojo(mojo,
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
                .getResource(PLUGIN_CONFIG_SKIP_XML)).getFile());

        GenerateLambdaConfigGoal mojo = new GenerateLambdaConfigGoal();
        mojo = (GenerateLambdaConfigGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));

        assertArrayEquals(new String[]{"com.syndicate"}, mojo.getPackages());
    }

    @Test
    public void testPluginExecuted() throws Exception {

        @LambdaHandler(tracingMode = TracingMode.Active,
                lambdaName = "lambda_execute_notification",
                roleName = "lr_get_notification_content")
        @EnvironmentVariable(key = "name", value = "lambda_execute_notification")
        @DependsOn(name = "stackAuditTopic", resourceType = ResourceType.SNS_TOPIC)
        @SnsEventSource(targetTopic = "stackAuditTopic", regionScope = RegionScope.ALL)
        class SnsLambdaExecutor {
            // test lambda class to be processed
        }

        @LambdaHandler(tracingMode = TracingMode.Active,
                lambdaName = "lambda_process_notification",
                roleName = "lr_get_notification_content",
                methodName = "handle")
        @LambdaConcurrency(executions = 1)
        @EnvironmentVariable(key = "name", value = "lambda_process_notification")
        @DependsOn(name = "stackAuditTopic", resourceType = ResourceType.SNS_TOPIC)
        @SnsEventSource(targetTopic = "stackAuditTopic", regionScope = RegionScope.ALL)
        @DeadLetterConfiguration(resourceName = "lambda-dead-letter-queue-name",
                resourceType = DeadLetterResourceType.SQS)
        class SnsLambdaProcessor {
            // test lambda class to be processed
            public void handle() {
                // method handler
            }
        }

        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource("plugin-config.xml")).getFile());

        GenerateLambdaConfigGoal mojo = new GenerateLambdaConfigGoal();
        mojo = (GenerateLambdaConfigGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(PLUGIN_ARTIFACT_ID, pluginConfig));

        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getCompileClasspathElements()).thenReturn(Arrays.asList("dep1", "dep2"));
        final Build build = mock(Build.class);
        final File file = mock(File.class);
        when(mavenProject.getBuild()).thenReturn(build);
        when(mavenProject.getBuild().getFinalName()).thenReturn("test");
        when(mavenProject.getVersion()).thenReturn("1.0.0");
        when(mavenProject.getBasedir()).thenReturn(file);

        File targetDir = folder.newFolder("target");
        when(mavenProject.getBasedir().getAbsolutePath()).thenReturn(folder.getRoot().getAbsolutePath());

        mojo.setProject(mavenProject);
        // override packages to process only current class file
        mojo.setPackages(new String[]{"com.syndicate.deployment.success"});

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
                .withTracingMode(TracingMode.Active.getMode())
                .withMemory(1024)
                .withFunction(SnsLambdaExecutor.class.getName())
                .withPackageName("test.jar")
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
                .build();

        // lambda_process_notification
        LambdaConfiguration snsLambdaProcessorConfiguration = new LambdaConfiguration.Builder()
                .withTracingMode(TracingMode.Active.getMode())
                .withMemory(1024)
                .withFunction(SnsLambdaProcessor.class.getName() + ":handle")
                .withPackageName("test.jar")
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
                .build();


        File deploymentResourcesFile = Arrays.stream(files).filter(f -> f.getName()
                .equalsIgnoreCase("deployment_resources.json"))
                .findFirst().get();

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

}
