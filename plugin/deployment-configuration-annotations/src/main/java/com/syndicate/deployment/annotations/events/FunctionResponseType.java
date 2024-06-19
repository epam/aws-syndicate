package com.syndicate.deployment.annotations.events;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Map;
import java.util.Optional;

public enum FunctionResponseType {

    REPORT_BATCH_ITEM_FAILURES("ReportBatchItemFailures");

    private final String jsonValue;
    private final static Map<String, FunctionResponseType> map = Map.of(
            "ReportBatchItemFailures",
            REPORT_BATCH_ITEM_FAILURES
    );

    FunctionResponseType(String jsonValue) {
        this.jsonValue = jsonValue;
    }

    @JsonCreator
    public static FunctionResponseType fromValue(String value) {
        return Optional.ofNullable(map.get(value)).orElseThrow();
    }

    @JsonValue
    public String getJsonValue() {
        return jsonValue;
    }
}
