package com.syndicate.deployment.model;

public enum LambdaSnapStart {
    PublishedVersions("PublishedVersions"),
    None("None");

    final String value;

    LambdaSnapStart(String value) {
        this.value = value;
    }
}
