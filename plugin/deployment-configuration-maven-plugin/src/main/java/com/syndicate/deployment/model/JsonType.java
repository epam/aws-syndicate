package com.syndicate.deployment.model;

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

    public String getTypeName() {
        return typeName;
    }
}
