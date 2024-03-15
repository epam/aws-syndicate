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

import com.fasterxml.jackson.annotation.JsonProperty;
import com.syndicate.deployment.model.EventSourceType;

import java.util.Objects;

/**
 * Created by Roman Ivanov on 2/22/2024.
 */
public class EventBridgeRuleSourceItem extends EventSourceItem {

    @JsonProperty("target_rule")
    private String targetRule;

    public EventBridgeRuleSourceItem() {
    }

    public String getTargetRule() {
        return targetRule;
    }

    public static class Builder {

        private final EventBridgeRuleSourceItem eventBridgeRuleSourceItem = new EventBridgeRuleSourceItem();

        public Builder withTargetRule(String targetRule) {
            Objects.requireNonNull(targetRule, "TargetSchedule cannot be null");
            eventBridgeRuleSourceItem.targetRule = targetRule;
            return this;
        }

        public EventBridgeRuleSourceItem build() {
            eventBridgeRuleSourceItem.eventSourceType = EventSourceType.EVENTBRIDGE_RULE_TRIGGER;
            return eventBridgeRuleSourceItem;
        }
    }

    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        EventBridgeRuleSourceItem that = (EventBridgeRuleSourceItem) o;
        return eventSourceType == that.eventSourceType && targetRule.equals(that.targetRule);
    }

    @Override
    public int hashCode() {
        return targetRule.hashCode() + eventSourceType.hashCode();
    }

    @Override
    public String toString() {
        return "EventBridgeRuleSourceItem{" +
                "targetRule='" + targetRule + '\'' +
                "} " + super.toString();
    }
}
