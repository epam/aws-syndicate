package com.syndicate.deployment.model.lambda.url;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Created by Roman Ivanov on 2023-11-07
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class UrlConfig {

    @JsonProperty("auth_type")
    private final AuthType authType;

    @JsonProperty("invoke_mode")
    private final InvokeMode invokeMode;

    public UrlConfig(AuthType authType, InvokeMode invokeMode) {
        this.authType = authType;
        this.invokeMode = invokeMode;
    }

    public AuthType getAuthType() {
        return authType;
    }

    public InvokeMode getInvokeMode() {
        return invokeMode;
    }

    @Override
    public String toString() {
        return "UrlConfig{" +
                "authType=" + authType +
                ", invokeMode=" + invokeMode +
                '}';
    }

}
