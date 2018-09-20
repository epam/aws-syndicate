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

/**
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
public class LambdaProperties {

    private final String name;
    private final String roleName;

    public LambdaProperties(String name, String roleName) {
        this.name = name;
        this.roleName = roleName;
    }

    public String getName() {
        return name;
    }

    public String getRoleName() {
        return roleName;
    }

    @Override
    public String toString() {
        return "LambdaProperties{" +
                "name='" + name + '\'' +
                ", roleName='" + roleName + '\'' +
                '}';
    }

}
