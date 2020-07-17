package com.syndicate.deployment.model;


import com.fasterxml.jackson.annotation.JsonValue;

public enum JsonType {

    LIST("array"),
    BOOL("boolean"),
    NUMBER("number"),
    INTEGER("integer"),
    OBJECT("object"),
    STRING("string");

    private final String typeName;

    JsonType(String typeName) {
        this.typeName = typeName;
    }

    @JsonValue
    public String getTypeName() {
        return typeName;
    }
}
