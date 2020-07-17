package com.syndicate.deployment.goal;

import com.syndicate.deployment.model.JsonSchema;
import com.syndicate.deployment.processor.IAnnotationProcessor;
import com.syndicate.deployment.processor.impl.DynamoDBDocumentAnnotationProcessor;
import com.syndicate.deployment.utils.JsonUtils;
import com.syndicate.deployment.utils.ProjectUtils;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.ResolutionScope;

import java.io.IOException;
import java.util.Map;

@Mojo(name = "generate-dynamodb-schemes", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class GenerateDynamoDbSchemesGoal extends AbstractMetaGoal {

    IAnnotationProcessor<JsonSchema> dynamoDbDocumentAnnotationProcessor;

    public GenerateDynamoDbSchemesGoal() {
        this.dynamoDbDocumentAnnotationProcessor = new DynamoDBDocumentAnnotationProcessor();
    }

    @Override
    public void executeGoal(String absolutePath) throws MojoExecutionException, IOException {
        logger.info("generate-dynamodb-schemes started");
        Map<String, JsonSchema> dynamoDbSchemes =
                dynamoDbDocumentAnnotationProcessor.generateMeta(absolutePath, packages, project.getVersion(), this.fileName);
        if (!dynamoDbSchemes.isEmpty()) {
            String targetFolderPath = ProjectUtils.getRootDirPath(project);
            writeToFile(targetFolderPath, "json_schemes.json", JsonUtils.convertToJson(dynamoDbSchemes));
        }
    }
}
