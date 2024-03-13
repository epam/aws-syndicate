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

package com.syndicate.deployment.model;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Created by Vladyslav Tereshchenko on 10/6/2016.
 */
public enum DeploymentRuntime {

    @Deprecated(forRemoval = true)
    JAVA8("java8"),
    JAVA11("java11"),
    JAVA17("java17"),
    JAVA21("java21"),
    PYTHON("python2.7"),
    NODEJS43("nodejs4.3"),
    NODEJS("nodejs");

    String name;

    DeploymentRuntime(String name) {
        this.name = name;
    }

    @JsonValue
    public String getName() {
        return name;
    }

    @Override
    public String toString() {
        return "DeploymentRuntime{" +
                "name='" + name + '\'' +
                '}';
    }

}
