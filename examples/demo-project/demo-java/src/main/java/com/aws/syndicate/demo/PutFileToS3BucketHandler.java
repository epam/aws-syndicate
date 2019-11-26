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
package com.aws.syndicate.demo;

import com.amazonaws.services.dynamodbv2.document.internal.InternalUtils;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.DynamodbEvent;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.environment.EnvironmentVariables;
import com.syndicate.deployment.annotations.events.DynamoDbTriggerEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.model.ResourceType;

import java.util.Map;

/**
 * Created by Vladyslav Tereshchenko on 9/12/2018.
 */
@LambdaHandler(lambdaName = "dynamodb_item_processor",
    roleName = "PutObjectToS3Role",
    layers = {"layer1", "layer2", "layer3"}
)
@DynamoDbTriggerEventSource(targetTable = "Notifications", batchSize = 1)
@DependsOn(name = "Notifications", resourceType = ResourceType.DYNAMODB_TABLE)
@EnvironmentVariables(value = {
        @EnvironmentVariable(key = "region", value = "${region}"),
        @EnvironmentVariable(key = "notification_bucket", value = "${notification_bucket}")
})
public class PutFileToS3BucketHandler implements RequestHandler<DynamodbEvent, Void> {

    private static final String INSERT = "INSERT";

    private AmazonS3 s3Client;
    private ObjectMapper objectMapper;

    public PutFileToS3BucketHandler() {
        this.s3Client = AmazonS3Client.builder().withRegion(System.getenv("region")).build();
        this.objectMapper = new ObjectMapper();
    }

    public Void handleRequest(DynamodbEvent dynamodbEvent, Context context) {
        String bucketName = System.getenv("notification_bucket");
        for (DynamodbEvent.DynamodbStreamRecord record : dynamodbEvent.getRecords()) {
            if (INSERT.equals(record.getEventName())) {
                Map<String, Object> stringObjectMap = InternalUtils.toSimpleMapValue(record.getDynamodb()
                        .getNewImage());
                s3Client.putObject(bucketName, (String) stringObjectMap.get("id"),
                        convertObjectToJson(stringObjectMap));
            }
        }
        return null;
    }

    private String convertObjectToJson(Object object) {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Object cannot be converted to JSON: " + object);
        }
    }

}
