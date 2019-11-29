package com.syndicate.deployment.model.api.request;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Created by Vladyslav Tereshchenko on 2/8/2019.
 */
public class SaveMetaRequest {

    @JsonProperty("build_id")
    private String buildId;

    @JsonProperty("build_time")
    private long buildTime;

    private List<Object> body;

    public SaveMetaRequest(String buildId, long buildTime, List<Object> body) {
        this.buildId = buildId;
        this.buildTime = buildTime;
        this.body = body;
    }

    public String getBuildId() {
        return buildId;
    }

    public long getBuildTime() {
        return buildTime;
    }

    public List<Object> getBody() {
        return body;
    }

    @Override
    public String toString() {
        return "SaveMetaRequest{" +
                "buildId='" + buildId + '\'' +
                ", buildTime=" + buildTime +
                ", body=" + body +
                '}';
    }

}
