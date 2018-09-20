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
 * Created by Vladyslav Tereshchenko on 10/12/2016.
 */
public class RuleEventSourceItem extends EventSourceItem {

    @JsonProperty("target_rule")
    private String targetRule;

    private RuleEventSourceItem() {
    }

    public String getTargetRule() {
        return targetRule;
    }

    public static class Builder {

        private final RuleEventSourceItem ruleEventSourceItem = new RuleEventSourceItem();

        public Builder withTargetRule(String targetRule) {
            Objects.requireNonNull(targetRule, "TargetSchedule cannot be null");
            ruleEventSourceItem.targetRule = targetRule;
            return this;
        }

        public RuleEventSourceItem build() {
            ruleEventSourceItem.eventSourceType = EventSourceType.CLOUDWATCH_RULE_TRIGGER;
            return ruleEventSourceItem;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        RuleEventSourceItem that = (RuleEventSourceItem) o;
        return eventSourceType == that.eventSourceType && targetRule.equals(that.targetRule);

    }

    @Override
    public int hashCode() {
        return targetRule.hashCode() + eventSourceType.hashCode();
    }

    @Override
    public String toString() {
        return "RuleEventSourceItem{" +
                "targetRule='" + targetRule + '\'' +
                "} " + super.toString();
    }

}
