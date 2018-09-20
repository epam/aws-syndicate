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

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Objects;

/**
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
public class DependencyItem {

    @JsonProperty("resource_name")
    private String resourceName;

    @JsonProperty("resource_type")
    private ResourceType resourceType;

    private DependencyItem() {
    }

    public String getResourceName() {
        return resourceName;
    }

    public ResourceType getResourceType() {
        return resourceType;
    }

    public static class Builder {

        private final DependencyItem dependencyItem = new DependencyItem();

        public Builder withResourceName(String resourceName) {
            Objects.requireNonNull(resourceName, "ResourceName cannot be null");
            dependencyItem.resourceName = resourceName;
            return this;
        }

        public Builder withResourceType(ResourceType resourceType) {
            Objects.requireNonNull(resourceType, "ResourceType cannot be null");
            dependencyItem.resourceType = resourceType;
            return this;
        }

        public DependencyItem build() {
            return dependencyItem;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DependencyItem that = (DependencyItem) o;

        return resourceName.equals(that.resourceName) && resourceType == that.resourceType;

    }

    @Override
    public int hashCode() {
        int result = resourceName.hashCode();
        result = 31 * result + resourceType.hashCode();
        return result;
    }

    @Override
    public String toString() {
        return "DependencyItem{" +
                "resourceName='" + resourceName + '\'' +
                ", eventSourceType=" + resourceType +
                '}';
    }

}
