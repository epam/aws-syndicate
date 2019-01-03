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

package com.syndicate.deployment.fail;

import com.syndicate.deployment.goal.impl.GenerateLambdaConfigGoal;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.events.SnsEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.model.RegionScope;
import com.syndicate.deployment.model.ResourceType;
import com.syndicate.deployment.model.TracingMode;
import com.syndicate.deployment.success.GenerateLambdaConfigMojoSuccessTest;
import org.apache.maven.artifact.DependencyResolutionRequiredException;
import org.apache.maven.model.Build;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.testing.MojoRule;
import org.apache.maven.project.MavenProject;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.util.Arrays;
import java.util.Objects;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Created by Vladyslav Tereshchenko on 8/31/2018.
 */
public class GenerateLambdaConfigMojoFailTest {

    @Rule
    public MojoRule rule = new MojoRule();

    @Rule
    public TemporaryFolder folder = new TemporaryFolder(new File("."));

    private GenerateLambdaConfigGoal mojo = new GenerateLambdaConfigGoal();

    @Before
    public void setUp() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(getClass().getClassLoader()
                .getResource("plugin-config-syndicate-goal.xml")).toURI());

        mojo = (GenerateLambdaConfigGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(GenerateLambdaConfigMojoSuccessTest.PLUGIN_ARTIFACT_ID, pluginConfig));
    }

    @Test(expected = MojoExecutionException.class)
    public void testPluginClasspathExceptionThrown() throws Exception {
        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getBuild()).thenReturn(mock(Build.class));
        // build situation when smth went wrong with the dependencies
        when(mavenProject.getCompileClasspathElements()).thenThrow(DependencyResolutionRequiredException.class);
        final Build build = mock(Build.class);
        when(mavenProject.getBuild()).thenReturn(build);
        when(build.getFinalName()).thenReturn("test_lambda");
        mojo.setProject(mavenProject);
        mojo.execute();
    }

    @Test(expected = MojoExecutionException.class)
    public void testPluginLambdaNamesUniqueExceptionThrown() throws Exception {

        @LambdaHandler(tracingMode = TracingMode.Active,
                lambdaName = "lambda_get_notification_content",
                roleName = "lr_get_notification_content")
        @EnvironmentVariable(key = "name", value = "lambda_get_notification_content")
        @DependsOn(name = "stackAuditTopic", resourceType = ResourceType.SNS_TOPIC)
        @SnsEventSource(targetTopic = "stackAuditTopic", regionScope = RegionScope.ALL)
        class SnsLambdaExecutor {
            // test lambda class to be processed
        }

        @LambdaHandler(tracingMode = TracingMode.Active,
                lambdaName = "lambda_get_notification_content",
                roleName = "lr_get_notification_content")
        @EnvironmentVariable(key = "name", value = "lambda_get_notification_content")
        @DependsOn(name = "stackAuditTopic", resourceType = ResourceType.SNS_TOPIC)
        @SnsEventSource(targetTopic = "stackAuditTopic", regionScope = RegionScope.ALL)
        class SnsLambdaProcessor {
            // test lambda class to be processed
        }

        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getBuild()).thenReturn(mock(Build.class));
        when(mavenProject.getCompileClasspathElements()).thenReturn(Arrays.asList("dep1", "dep2"));
        final Build build = mock(Build.class);
        final File file = mock(File.class);
        when(mavenProject.getBuild()).thenReturn(build);
        when(mavenProject.getVersion()).thenReturn("1.0.0");
        when(mavenProject.getBasedir()).thenReturn(file);

        // lambda config should be present
        folder.newFolder("target");
        folder.newFile("lambda_get_notification_content_lambda_config.json");

        when(mavenProject.getBasedir().getAbsolutePath()).thenReturn(folder.getRoot().getAbsolutePath());
        mojo.setProject(mavenProject);
        // override packages to process only current class file
        mojo.setPackages(new String[]{"com.syndicate.deployment.fail"});
        mojo.setFileName("kjhgf");

        mojo.execute();
    }

}
