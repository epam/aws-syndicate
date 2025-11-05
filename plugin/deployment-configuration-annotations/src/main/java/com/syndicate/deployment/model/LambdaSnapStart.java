package com.syndicate.deployment.model;

public enum LambdaSnapStart {
    PublishedVersions("published_versions"),
    None("NONE");

    final String value;

    LambdaSnapStart(String value) {
        this.value = value;
    }
}
