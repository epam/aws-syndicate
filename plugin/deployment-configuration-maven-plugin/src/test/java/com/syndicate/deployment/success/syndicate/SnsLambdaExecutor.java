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
package com.syndicate.deployment.success.syndicate;

import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.events.SnsEventSource;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.annotations.resources.DependsOn;
import com.syndicate.deployment.annotations.tag.Tag;
import com.syndicate.deployment.annotations.tag.Tags;
import com.syndicate.deployment.model.LambdaSnapStart;
import com.syndicate.deployment.model.RegionScope;
import com.syndicate.deployment.model.ResourceType;
import com.syndicate.deployment.model.TracingMode;

/**
 * Created by Oleksandr Onsha on 10/30/18
 */
@LambdaHandler(tracingMode = TracingMode.Active,
        lambdaName = "lambda_execute_notification",
        roleName = "lr_get_notification_content",
        snapStart = LambdaSnapStart.PublishedVersions
)
@EnvironmentVariable(key = "name", value = "lambda_execute_notification")
@DependsOn(name = "stackAuditTopic", resourceType = ResourceType.SNS_TOPIC)
@SnsEventSource(targetTopic = "stackAuditTopic", regionScope = RegionScope.ALL)
@Tags(value = {@Tag(key = "key", value = "value")})
public class SnsLambdaExecutor {
    // test lambda class to be processed
}
