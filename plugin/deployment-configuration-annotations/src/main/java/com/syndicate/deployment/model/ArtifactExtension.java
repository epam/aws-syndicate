package com.syndicate.deployment.model;

public enum ArtifactExtension {

    ZIP,
    JAR;

    String extension;

    ArtifactExtension() {
        this.extension = String.format(".%s", this.name().toLowerCase());
    }

    public String getExtension() {
        return extension;
    }
}
