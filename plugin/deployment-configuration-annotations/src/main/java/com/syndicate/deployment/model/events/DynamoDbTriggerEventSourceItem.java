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
public class DynamoDbTriggerEventSourceItem extends EventSourceItem {

    @JsonProperty("target_table")
    private String targetTable;

    @JsonProperty("batch_size")
    private int batchSize;

    private DynamoDbTriggerEventSourceItem() {
    }

    public String getTargetTable() {
        return targetTable;
    }

    public int getBatchSize() {
        return batchSize;
    }

    public static class Builder {

        private final DynamoDbTriggerEventSourceItem triggerEventSourceItem = new DynamoDbTriggerEventSourceItem();

        public Builder withTargetTable(String targetTable) {
            Objects.requireNonNull(targetTable, "TargetTable cannot be null");
            triggerEventSourceItem.targetTable = targetTable;
            return this;
        }

        public Builder withBatchSize(int batchSize) {
            Objects.requireNonNull(batchSize, "BatchSize cannot be null");
            triggerEventSourceItem.batchSize = batchSize;
            return this;
        }

        public DynamoDbTriggerEventSourceItem build() {
            triggerEventSourceItem.eventSourceType = EventSourceType.DYNAMODB_TRIGGER;
            return triggerEventSourceItem;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DynamoDbTriggerEventSourceItem that = (DynamoDbTriggerEventSourceItem) o;

        return batchSize == that.batchSize && eventSourceType == that.eventSourceType && targetTable.equals(that.targetTable);

    }

    @Override
    public int hashCode() {
        int result = targetTable.hashCode();
        result = 31 * result + eventSourceType.hashCode();
        result = 31 * result + batchSize;
        return result;
    }

    @Override
    public String toString() {
        return "DynamoDbTriggerEventSourceItem{" +
                "targetTable='" + targetTable + '\'' +
                ", batchSize=" + batchSize +
                "} " + super.toString();
    }

}
