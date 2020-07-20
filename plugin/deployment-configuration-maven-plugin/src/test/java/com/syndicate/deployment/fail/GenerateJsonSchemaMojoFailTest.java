package com.syndicate.deployment.fail;

import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBAttribute;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBHashKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBTable;
import com.syndicate.deployment.goal.GenerateDynamoDbSchemesGoal;
import com.syndicate.deployment.success.GenerateLambdaConfigMojoSuccessTest;
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
import java.util.Properties;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class GenerateJsonSchemaMojoFailTest {


    @Rule
    public MojoRule rule = new MojoRule();

    @Rule
    public TemporaryFolder folder = new TemporaryFolder(new File("."));

    private GenerateDynamoDbSchemesGoal mojo = new GenerateDynamoDbSchemesGoal();

    private Properties EMPTY_PROPERTIES = new Properties();

    @Before
    public void setUp() throws Exception {
        File pluginConfig = new File(Objects.requireNonNull(
                getClass().getClassLoader().getResource("plugin-config-dynamodb-goal.xml")).toURI());

        mojo = (GenerateDynamoDbSchemesGoal) rule.configureMojo(mojo,
                rule.extractPluginConfiguration(
                        GenerateLambdaConfigMojoSuccessTest.PLUGIN_ARTIFACT_ID, pluginConfig));
    }


    @Test(expected = MojoExecutionException.class)
    public void testPluginTableNamesUniqueExceptionThrown() throws Exception {

        @DynamoDBTable(tableName = "TestTable")
        class TestTable {

            @DynamoDBHashKey(attributeName = "hk")
            private String hashKey;

            @DynamoDBAttribute(attributeName = "field1")
            private int field1DiffName;
        }

        @DynamoDBTable(tableName = "TestTable")
        class TestTable2 {

            @DynamoDBHashKey(attributeName = "hk")
            private String hashKey;

            @DynamoDBAttribute(attributeName = "field2")
            private int field2DiffName;
        }

        final MavenProject mavenProject = mock(MavenProject.class);
        when(mavenProject.getBuild()).thenReturn(mock(Build.class));
        when(mavenProject.getCompileClasspathElements()).thenReturn(Arrays.asList("dep1", "dep2"));
        final Build build = mock(Build.class);
        final File file = mock(File.class);
        when(mavenProject.getBuild()).thenReturn(build);
        when(mavenProject.getVersion()).thenReturn("1.0.0");
        when(mavenProject.getBasedir()).thenReturn(file);
        when(mavenProject.getParent()).thenReturn(mavenProject);
        when(mavenProject.getProperties()).thenReturn(EMPTY_PROPERTIES);

        // lambda config should be present
        when(mavenProject.getBasedir().getAbsolutePath()).thenReturn(folder.getRoot().getAbsolutePath());
        mojo.setProject(mavenProject);
        // override packages to process only current class file
        mojo.setPackages(new String[]{"com.syndicate.deployment.fail"});

        mojo.execute();
    }

}
