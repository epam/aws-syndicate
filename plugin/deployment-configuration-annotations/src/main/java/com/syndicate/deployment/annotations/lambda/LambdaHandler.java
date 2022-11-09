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


import com.syndicate.deployment.annotations.DeploymentResource;
import com.syndicate.deployment.model.DeploymentRuntime;
import com.syndicate.deployment.model.RegionScope;
import com.syndicate.deployment.model.TracingMode;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
@DeploymentResource
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface LambdaHandler {

    String lambdaName();

    String roleName();

    /**
     * Required if class does not implement sdk interface
     */
    String methodName() default "";

    DeploymentRuntime runtime() default DeploymentRuntime.JAVA8;

    int timeout() default 300;

    int memory() default 1024;

    RegionScope regionScope() default RegionScope.DEFAULT;

    String[] subnetsIds() default {};

    String[] securityGroupIds() default {};

    TracingMode tracingMode() default TracingMode.NoTracing;

    boolean isPublishVersion() default false;

    String aliasName() default "";

    String[] layers() default {};

}
