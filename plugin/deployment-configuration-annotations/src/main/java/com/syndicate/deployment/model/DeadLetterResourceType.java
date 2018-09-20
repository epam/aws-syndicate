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
 * Created by Oleksandr Onsha on 8/9/18
 */
public enum DeadLetterResourceType {

    SNS("sns"),
    SQS("sqs");

    private String serviceName;

    DeadLetterResourceType(String serviceName) {
        this.serviceName = serviceName;
    }

    @JsonValue
    public String getServiceName() {
        return this.serviceName;
    }

    @Override
    public String toString() {
        return "DeadLetterResourceType{" +
                "serviceName='" + serviceName + '\'' +
                '}';
    }
}