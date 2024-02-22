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
import com.syndicate.deployment.annotations.events.DynamoDbTriggerEventSource;
import com.syndicate.deployment.annotations.events.EventBridgeRuleSource;
import com.syndicate.deployment.annotations.events.RuleEventSource;
import com.syndicate.deployment.annotations.events.S3EventSource;
import com.syndicate.deployment.annotations.events.SnsEventSource;
import com.syndicate.deployment.annotations.events.SqsTriggerEventSource;
import com.syndicate.deployment.model.events.DynamoDbTriggerEventSourceItem;
import com.syndicate.deployment.model.events.EventBridgeRuleSourceItem;
import com.syndicate.deployment.model.events.EventSourceItem;
import com.syndicate.deployment.model.events.RuleEventSourceItem;
import com.syndicate.deployment.model.events.S3EventSourceItem;
import com.syndicate.deployment.model.events.SnsTriggerEventSourceItem;
import com.syndicate.deployment.model.events.SqsTriggerEventSourceItem;

import java.lang.annotation.Annotation;

/**
 * Created by Vladyslav Tereshchenko on 10/13/2016.
 */
public enum EventSourceType {

    CLOUDWATCH_RULE_TRIGGER("cloudwatch_rule_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            return new RuleEventSourceItem.Builder()
                    .withTargetRule(((RuleEventSource) eventSource).targetRule()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((RuleEventSource) eventSource).targetRule())
                    .withResourceType(ResourceType.CLOUDWATCH_RULE).build();
        }
    },

    EVENTBRIDGE_RULE_TRIGGER("eventbridge_rule_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            return new EventBridgeRuleSourceItem.Builder()
                    .withTargetRule(((EventBridgeRuleSource) eventSource).targetRule()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((EventBridgeRuleSource) eventSource).targetRule())
                    .withResourceType(ResourceType.EVENTBRIDGE_RULE).build();
        }
    },

    DYNAMODB_TRIGGER("dynamodb_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            DynamoDbTriggerEventSource dbTriggerEventSource = (DynamoDbTriggerEventSource) eventSource;
            return new DynamoDbTriggerEventSourceItem.Builder()
                    .withTargetTable(dbTriggerEventSource.targetTable())
                    .withBatchSize(dbTriggerEventSource.batchSize()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((DynamoDbTriggerEventSource) eventSource).targetTable())
                    .withResourceType(ResourceType.DYNAMODB_TABLE).build();
        }
    },
    S3_TRIGGER("s3_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            S3EventSource s3EventSource = (S3EventSource) eventSource;
            return new S3EventSourceItem.Builder()
                    .withTargetBucket(s3EventSource.targetBucket())
                    .withEvents(s3EventSource.events()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((S3EventSource) eventSource).targetBucket())
                    .withResourceType(ResourceType.S3_BUCKET).build();
        }
    },
    SNS_TOPIC_TRIGGER("sns_topic_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            SnsEventSource snsEventSource = (SnsEventSource) eventSource;
            return new SnsTriggerEventSourceItem.Builder()
                    .withTargetTopic(snsEventSource.targetTopic())
                    .withRegionScope(snsEventSource.regionScope()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((SnsEventSource) eventSource).targetTopic())
                    .withResourceType(ResourceType.SNS_TOPIC).build();
        }
    },
    SQS_TRIGGER("sqs_trigger") {
        @Override
        public EventSourceItem createEventSourceItem(Annotation eventSource) {
            SqsTriggerEventSource sqsEventSource = (SqsTriggerEventSource) eventSource;
            return new SqsTriggerEventSourceItem.Builder()
                    .withTargetQueue(sqsEventSource.targetQueue())
                    .withBatchSize(sqsEventSource.batchSize()).build();
        }

        @Override
        public DependencyItem createDependencyItem(Annotation eventSource) {
            return new DependencyItem.Builder()
                    .withResourceName(((SqsTriggerEventSource) eventSource).targetQueue())
                    .withResourceType(ResourceType.SQS_QUEUE)
                    .build();
        }
    };

    String name;

    EventSourceType(String name) {
        this.name = name;
    }

    @JsonValue
    public String getName() {
        return name;
    }

    public abstract EventSourceItem createEventSourceItem(Annotation eventSource);

    public abstract DependencyItem createDependencyItem(Annotation eventSource);

    @Override
    public String toString() {
        return "EventSourceType{" +
                "name='" + name + '\'' +
                '}';
    }

}
