package com.syndicate.deployment.annotations.events;

public enum FunctionResponseType {
    REPORT_BATCH_ITEM_FAILURES("ReportBatchItemFailures");

    private final String stringValue;

    FunctionResponseType(String stringValue) {
        this.stringValue = stringValue;
    }

    @Override
    public String toString() {
        return stringValue;
    }
}
