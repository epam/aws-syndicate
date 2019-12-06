package com.syndicate.deployment.api.model.response;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Created by Vladyslav Tereshchenko on 2/8/2019.
 */
public class SaveMetaResponse {

    private String message;

    @JsonProperty("resources_count")
    private int resourcesCount;

    @JsonProperty("build_id")
    private String buildId;

    @JsonProperty("resources_names")
    private List<String> resourceNames;

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public int getResourcesCount() {
        return resourcesCount;
    }

    public void setResourcesCount(int resourcesCount) {
        this.resourcesCount = resourcesCount;
    }

    public String getBuildId() {
        return buildId;
    }

    public void setBuildId(String buildId) {
        this.buildId = buildId;
    }

    public List<String> getResourceNames() {
        return resourceNames;
    }

    public void setResourceNames(List<String> resourceNames) {
        this.resourceNames = resourceNames;
    }

}
