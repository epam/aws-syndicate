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
package com.demojava;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.environment.EnvironmentVariables;
import com.syndicate.deployment.annotations.events.DynamoDbTriggerEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.LambdaSnapStart;
import com.syndicate.deployment.model.ResourceType;
import com.syndicate.deployment.model.RetentionSetting;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.core.sync.RequestBody;

/**
 * Created by Vladyslav Tereshchenko on 9/12/2018.
 */
@LambdaHandler(
        logsExpiration = RetentionSetting.SYNDICATE_ALIASES_SPECIFIED,
        lambdaName = "dynamodb_item_processor",
        roleName = "PutObjectToS3Role",
        runtime = DeploymentRuntime.JAVA11,
        snapStart = LambdaSnapStart.PublishedVersions
)
@DynamoDbTriggerEventSource(targetTable = "Notifications", batchSize = 1)
@DependsOn(name = "Notifications", resourceType = ResourceType.DYNAMODB_TABLE)
@EnvironmentVariables(value = {
        @EnvironmentVariable(key = "region", value = "${region}"),
        @EnvironmentVariable(key = "notification_bucket", value = "${notification_bucket}")
})
public class PutFileToS3BucketHandler implements RequestHandler<Map<String, Object>, Void> {

    private final S3Client s3Client;
    private final ObjectMapper objectMapper;

    public PutFileToS3BucketHandler() {
        this.s3Client = S3Client.builder()
                .region(Region.of(System.getenv("region")))
                .build();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public Void handleRequest(Map<String, Object> event, Context context) {
        String bucketName = System.getenv("notification_bucket");

        // Parse the event manually (structure depends on DynamoDB Streams event JSON)
        List<Map<String, Object>> records = (List<Map<String, Object>>) event.get("Records");
        if (records == null) return null;

        for (Map<String, Object> record : records) {
            String eventName = (String) record.get("eventName");
            if (!"INSERT".equals(eventName)) continue;

            Map<String, Object> dynamodb = (Map<String, Object>) record.get("dynamodb");
            Map<String, Object> newImage = (Map<String, Object>) dynamodb.get("NewImage");

            // You need to parse DynamoDB AttributeValue JSON structure here!
            // For example, if your id is a string:
            Map<String, Object> idMap = (Map<String, Object>) newImage.get("id");
            String id = (String) idMap.get("S");

            // Convert the whole newImage to JSON string
            String json = convertObjectToJson(newImage);

            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(id)
                    .build();

            s3Client.putObject(
                    putObjectRequest,
                    RequestBody.fromBytes(json.getBytes(StandardCharsets.UTF_8))
            );
        }
        return null;
    }

    private String convertObjectToJson(Object object) {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (Exception e) {
            throw new IllegalArgumentException("Object cannot be converted to JSON: " + object);
        }
    }

}
