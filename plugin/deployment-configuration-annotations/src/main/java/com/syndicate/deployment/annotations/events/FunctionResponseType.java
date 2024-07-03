package com.syndicate.deployment.annotations.events;

import com.fasterxml.jackson.annotation.JsonValue;

public enum FunctionResponseType {

    REPORT_BATCH_ITEM_FAILURES("ReportBatchItemFailures");

    private final String jsonValue;

    FunctionResponseType(String jsonValue) {
        this.jsonValue = jsonValue;
    }

    @JsonValue
    public String getJsonValue() {
        return jsonValue;
    }
}
