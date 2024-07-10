package com.syndicate.deployment.model.environment;

public enum ValueTransformer {

    NONE(null, null, null),
    USER_POOL_NAME_TO_USER_POOL_ID( "resource_name", "cognito_idp", "id"),
    USER_POOL_NAME_TO_CLIENT_ID( "resource_name", "cognito_idp", "client_id");

    private final String sourceParameter;
    private final String resourceType;
    private final String parameter;

    ValueTransformer(String sourceParameter, String resourceType, String targetParameter) {
        this.sourceParameter = sourceParameter;
        this.resourceType = resourceType;
        this.parameter = targetParameter;
    }

    public String getSourceParameter() {
        return sourceParameter;
    }

    public String getResourceType() {
        return resourceType;
    }

    public String getParameter() {
        return parameter;
    }
}
