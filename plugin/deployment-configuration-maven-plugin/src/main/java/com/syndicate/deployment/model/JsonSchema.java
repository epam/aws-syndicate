package com.syndicate.deployment.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_EMPTY;

@JsonInclude(NON_EMPTY)
public class JsonSchema {

    public static final String DEFAULT_TYPE = "object";

    private final List<JsonType> type;


    private final Map<String, JsonSchema> properties = new HashMap<>();

    @JsonIgnore
    private String className;

    public JsonSchema() {
        type = Collections.singletonList(JsonType.OBJECT);
    }

    public JsonSchema(List<JsonType> type) {
        this.type = type;
    }

    public List<JsonType> getType() {
        return type;
    }

    public Map<String, JsonSchema> getProperties() {
        return properties;
    }

    public void addProperty(String name, List<JsonType> type) {
        properties.put(name, new JsonSchema(type));
    }

    public String getClassName() {
        return className;
    }

    public void setClassName(String className) {
        this.className = className;
    }

    @Override
    public String toString() {
        return "JsonSchema{" +
                "type='" + type + '\'' +
                ", properties=" + properties +
                ", className='" + className + '\'' +
                '}';
    }

    public void addObjectProperty(String name, JsonSchema objectSchema) {
        properties.put(name, objectSchema);
    }
}
