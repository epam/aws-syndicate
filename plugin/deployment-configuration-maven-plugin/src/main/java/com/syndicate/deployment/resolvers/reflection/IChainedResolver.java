package com.syndicate.deployment.resolvers.reflection;

import org.apache.maven.plugin.MojoExecutionException;

public interface IChainedResolver<IN, OUT> {
    OUT resolve(IN payload) throws MojoExecutionException;
}
