package com.syndicate.deployment.goal;

import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.logging.Log;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;
import org.apache.maven.project.MavenProject;

import java.util.UUID;

/**
 * Created by Vladyslav Tereshchenko on 2/12/2019.
 */
@Mojo(name = "gen-build-id", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class GenerateBuildIdGoal extends AbstractMojo {

    @Parameter(defaultValue = "${project}", required = true, readonly = true)
    private MavenProject project;

    private Log logger;

    public GenerateBuildIdGoal() {
        this.logger = getLog();
    }


    @Override
    public void execute() {
        logger.info("ROFLAN EBALO");
        String uuid = UUID.randomUUID().toString();
        logger.info(uuid);
        project.getProperties().setProperty("syndicate-build-id", uuid);
    }

}
