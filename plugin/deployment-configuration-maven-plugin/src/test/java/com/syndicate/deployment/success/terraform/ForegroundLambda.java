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
package com.syndicate.deployment.success.terraform;

import com.syndicate.deployment.annotations.environment.EnvironmentVariable;
import com.syndicate.deployment.annotations.lambda.LambdaHandler;
import com.syndicate.deployment.model.TracingMode;

/**
 * Created by Oleksandr Onsha on 10/30/18
 */
@LambdaHandler(tracingMode = TracingMode.Active,
        lambdaName = "foreground_lambda",
        roleName = "foreground-lambda-role")
@EnvironmentVariable(key = "name", value = "foreground_lambda")
public class ForegroundLambda {
    // test lambda class to be processed
}
