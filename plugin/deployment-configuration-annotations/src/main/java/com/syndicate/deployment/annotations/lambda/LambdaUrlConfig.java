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

package com.syndicate.deployment.annotations.lambda;

import com.syndicate.deployment.model.lambda.url.AuthType;
import com.syndicate.deployment.model.lambda.url.InvokeMode;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Enables Lambda function URL configuration for the annotated Lambda function.
 *
 * <p>Lambda function URLs are dedicated HTTP(S) endpoints for Lambda functions that allow
 * you to invoke functions via HTTP requests without using API Gateway or Application Load Balancer.
 * This annotation configures the authentication type and invoke mode for the function URL.</p>
 *
 * <p>For more information about Lambda function URLs, see the
 * <a href="https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html">
 * AWS Lambda function URLs documentation</a>.</p>
 *
 * @see AuthType
 * @see InvokeMode
 * @since 2023-11-07
 * @author Roman Ivanov
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface LambdaUrlConfig {

    /**
     * Specifies the authentication type for the Lambda function URL.
     *
     * @return the authentication type, defaults to {@link AuthType#NONE}
     */
    AuthType authType() default AuthType.NONE;

    /**
     * Specifies the invoke mode for the Lambda function URL.
     *
     * @return the invoke mode, defaults to {@link InvokeMode#BUFFERED}
     */
    InvokeMode invokeMode() default InvokeMode.BUFFERED;

}
