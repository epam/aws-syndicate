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

package com.syndicate.deployment.model.events;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.syndicate.deployment.model.EventSourceType;
import com.syndicate.deployment.model.RegionScope;

import java.util.Objects;

/**
 * Created by Vladyslav Tereshchenko on 12/9/2016.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SnsTriggerEventSourceItem extends EventSourceItem {

    @JsonProperty("target_topic")
    private String targetTopic;

    @JsonProperty("region")
    private String regionScope;

    private SnsTriggerEventSourceItem() {
    }

    public static class Builder {

        private final SnsTriggerEventSourceItem snsTriggerEventSourceItem = new SnsTriggerEventSourceItem();

        public Builder withTargetTopic(String targetTopic) {
            Objects.requireNonNull(targetTopic, "TargetTopic cannot be null");
            snsTriggerEventSourceItem.targetTopic = targetTopic;
            return this;
        }

        public Builder withRegionScope(RegionScope regionScope) {
            Objects.requireNonNull(regionScope, "Region scope cannot be null");
            snsTriggerEventSourceItem.regionScope = regionScope.getName();
            return this;
        }

        public SnsTriggerEventSourceItem build() {
            snsTriggerEventSourceItem.eventSourceType = EventSourceType.SNS_TOPIC_TRIGGER;
            return snsTriggerEventSourceItem;
        }

    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        SnsTriggerEventSourceItem that = (SnsTriggerEventSourceItem) o;

        return eventSourceType == that.eventSourceType && targetTopic.equals(that.targetTopic);

    }

    @Override
    public int hashCode() {
        return targetTopic.hashCode() + eventSourceType.hashCode();
    }

    @Override
    public String toString() {
        return "SnsTriggerEventSourceItem{" +
                "targetTopic='" + targetTopic + '\'' +
                "} " + super.toString();
    }

}
