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
 * Created by Vladyslav Tereshchenko on 10/5/2016.
 */
public class ScheduleEventSourceItem extends EventSourceItem {

    @JsonProperty("target_schedule")
    private String targetSchedule;

    private ScheduleEventSourceItem() {
    }

    public String getTargetSchedule() {
        return targetSchedule;
    }

    public static class Builder {

        private final ScheduleEventSourceItem scheduleEventSourceItem = new ScheduleEventSourceItem();

        public Builder withTargetSchedule(String targetSchedule) {
            Objects.requireNonNull(targetSchedule, "TargetSchedule cannot be null");
            scheduleEventSourceItem.targetSchedule = targetSchedule;
            return this;
        }

        public Builder withEventSourceType(EventSourceType eventSourceType) {
            Objects.requireNonNull(eventSourceType, "ResourceType cannot be null");
            scheduleEventSourceItem.eventSourceType = eventSourceType;
            return this;
        }

        public ScheduleEventSourceItem build() {
            return scheduleEventSourceItem;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        ScheduleEventSourceItem that = (ScheduleEventSourceItem) o;

        return eventSourceType == that.eventSourceType && targetSchedule.equals(that.targetSchedule);

    }

    @Override
    public int hashCode() {
        return targetSchedule.hashCode() + eventSourceType.hashCode();
    }

    @Override
    public String toString() {
        return "ScheduleEventSourceItem{" +
                "targetSchedule='" + targetSchedule + '\'' +
                "} " + super.toString();
    }

}
