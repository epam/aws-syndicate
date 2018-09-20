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
 * @author Dmytro_Skorniakov
 * Created on 1/5/2017.
 */
public enum RegionScope {

    DEFAULT(null),
    US_EAST_1("us-east-1"),
    US_WEST_2("us-west-2"),
    EU_WEST_1("eu-west-1"),
    AP_NORTHEAST_1("ap-northeast-1"),
    AP_SOUTHEAST_1("ap-southeast-1"),
    AP_SOUTHEAST_2("ap-southeast-2"),
    ALL("all");

    private String name;

    RegionScope(String name) {
        this.name = name;
    }

    @JsonValue
    public String getName() {
        return name;
    }

}
