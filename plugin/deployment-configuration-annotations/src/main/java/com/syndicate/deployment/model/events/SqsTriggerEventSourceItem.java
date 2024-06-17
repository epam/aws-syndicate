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
 * Created by Vladyslav Tereshchenko on 8/9/2018.
 */
public class SqsTriggerEventSourceItem extends EventSourceItem {

    @JsonProperty("target_queue")
    private String targetQueue;

    @JsonProperty("batch_size")
    private int batchSize;

    @JsonProperty("enable_batch_report_failures")
    private boolean enableBatchReportFailures;

    private SqsTriggerEventSourceItem() {
    }

    public String getTargetQueue() {
        return targetQueue;
    }

    public int getBatchSize() {
        return batchSize;
    }

    public boolean isEnableBatchReportFailures() {
        return enableBatchReportFailures;
    }

    public static class Builder {

        private final SqsTriggerEventSourceItem triggerEventSourceItem = new SqsTriggerEventSourceItem();

        public Builder withTargetQueue(String targetQueue) {
            Objects.requireNonNull(targetQueue, "TargetQueue cannot be null");
            triggerEventSourceItem.targetQueue = targetQueue;
            return this;
        }

        public Builder withBatchSize(int batchSize) {
            Objects.requireNonNull(batchSize, "BatchSize cannot be null");
            triggerEventSourceItem.batchSize = batchSize;
            return this;
        }

        public SqsTriggerEventSourceItem build() {
            triggerEventSourceItem.eventSourceType = EventSourceType.SQS_TRIGGER;
            return triggerEventSourceItem;
        }

        public Builder withEnableBatchReportFailures(boolean enableBatchReportFailures) {
            this.triggerEventSourceItem.enableBatchReportFailures = enableBatchReportFailures;
            return this;
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        SqsTriggerEventSourceItem that = (SqsTriggerEventSourceItem) o;

        return batchSize == that.batchSize && eventSourceType == that.eventSourceType && targetQueue.equals(that.targetQueue) && enableBatchReportFailures == that.enableBatchReportFailures;

    }

    @Override
    public int hashCode() {
        int result = targetQueue.hashCode();
        result = 31 * result + eventSourceType.hashCode();
        result = 31 * result + batchSize;
        result = 31 * result + Boolean.hashCode(enableBatchReportFailures);
        return result;
    }

    @Override
    public String toString() {
        return "SqsTriggerEventSourceItem{" +
                "targetQueue='" + targetQueue + '\'' +
                ", batchSize=" + batchSize +
                "} " + super.toString();
    }

}
