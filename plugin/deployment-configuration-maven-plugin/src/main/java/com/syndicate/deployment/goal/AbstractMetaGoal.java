package com.syndicate.deployment.goal;

import org.apache.maven.artifact.DependencyResolutionRequiredException;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugin.logging.Log;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.UnsupportedEncodingException;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public abstract class AbstractMetaGoal extends AbstractMojo {

    private static final String DEFAULT_ENCODING = "UTF-8";

    protected final Log logger;

    @Parameter(required = true)
    protected String fileName;

    @Parameter(defaultValue = "${project}", required = true, readonly = true)
    protected MavenProject project;

    @Parameter(property = "maven.processor.skip", defaultValue = "false")
    protected boolean skip;

    @Parameter(required = true)
    protected String[] packages;

    public AbstractMetaGoal() {
        this.logger = getLog();
    }

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            logger.info("lambda-configuration-processor is skipped");
            return;
        }
        logger.info("Start creating resources_config.json ...");
        logger.info("Path to deployment package ==> " + fileName);

        logger.debug("Creating custom classpath ...");

        Set<URI> uris = getUris();
        // creating custom classloader with specified module dependencies
        URL[] urlArray = getUrls(uris);
        try {
            try (URLClassLoader contextClassLoader = URLClassLoader.newInstance(urlArray,
                    Thread.currentThread().getContextClassLoader())) {
                // setting up created classpath as a current classloader
                Thread.currentThread().setContextClassLoader(contextClassLoader);
                String absolutePath = project.getBasedir().getAbsolutePath();
                executeGoal(absolutePath);
            }
        } catch (IOException e) {
            throw new MojoExecutionException("Goal execution failed", e);
        }
    }

    public abstract void executeGoal(String absolutePath) throws MojoExecutionException, IOException;

    public MavenProject getProject() {
        return project;
    }

    public void setProject(MavenProject project) {
        this.project = project;
    }

    public boolean isSkip() {
        return skip;
    }

    public void setSkip(boolean skip) {
        this.skip = skip;
    }

    public String[] getPackages() {
        return packages;
    }

    public void setPackages(String[] packages) {
        this.packages = packages;
    }

    protected void writeToFile(String folderPath, String fileName, String content) throws IOException {
        String filePath = folderPath + File.separator + fileName;
        try (PrintWriter printWriter = new PrintWriter(filePath, DEFAULT_ENCODING)) {
            printWriter.write(content);
        } catch (FileNotFoundException e) {
            throw new IOException("Cannot find file. Path ==> " + folderPath, e);
        } catch (UnsupportedEncodingException e) {
            throw new IOException("Incorrect encoding ==> " + DEFAULT_ENCODING, e);
        }
    }

    private Set<URI> getUris() throws MojoExecutionException {
        Set<URI> uris = new HashSet<>();
        try {
            // getting classpath of the current module
            List<String> elements = project.getCompileClasspathElements();
            // getting uris of the dependencies to inject into classloader
            // url presents file location of the dependency in the module
            for (String element : elements) {
                uris.add(new File(element).toURI());
            }
            logger.debug("Setting up new classloader ...");

        } catch (DependencyResolutionRequiredException e) {
            throw new MojoExecutionException("Dependency does not exist", e);
        }
        return uris;
    }

    private URL[] getUrls(Set<URI> uris) {
        return uris.stream()
                .map(uri -> {
                    try {
                        return uri.toURL();
                    } catch (MalformedURLException e) {
                        logger.error("Illegal protocol to URI. " + e.getMessage());
                        return null;
                    }
                }).toArray(URL[]::new);
    }
}
