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

import java.util.Arrays;
import java.util.Objects;

/**
 * Created by Vladyslav Tereshchenko on 11/1/2016.
 */
public class S3EventSourceItem extends EventSourceItem {

    @JsonProperty("target_bucket")
    private String targetBucket;

    @JsonProperty("s3_events")
    private String[] events;

    private S3EventSourceItem() {
    }

    public static class Builder {

        private final S3EventSourceItem s3EventSourceItem = new S3EventSourceItem();

        public Builder withTargetBucket(String targetBucket) {
            Objects.requireNonNull(targetBucket, "TargetBucket cannot be null");
            s3EventSourceItem.targetBucket = targetBucket;
            return this;
        }

        public Builder withEvents(String[] events) {
            Objects.requireNonNull(events, "Events cannot be null");
            if (events.length == 0) {
                throw new IllegalArgumentException("Events cannot be empty");
            }
            s3EventSourceItem.events = events;
            return this;
        }

        public S3EventSourceItem build() {
            s3EventSourceItem.eventSourceType = EventSourceType.S3_TRIGGER;
            return s3EventSourceItem;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        S3EventSourceItem that = (S3EventSourceItem) o;

        if (!targetBucket.equals(that.targetBucket)) return false;
        return eventSourceType == that.eventSourceType && Arrays.equals(events, that.events);

    }

    @Override
    public int hashCode() {
        int result = targetBucket.hashCode();
        result = 31 * result + eventSourceType.hashCode();
        result = 31 * result + Arrays.hashCode(events);
        return result;
    }

    @Override
    public String toString() {
        return "S3EventSourceItem{" +
                "targetBucket='" + targetBucket + '\'' +
                ", events=" + Arrays.toString(events) +
                "} " + super.toString();
    }

}
