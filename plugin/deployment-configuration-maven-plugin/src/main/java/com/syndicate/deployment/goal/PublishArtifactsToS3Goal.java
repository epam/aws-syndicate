package com.syndicate.deployment.goal;

import com.amazonaws.auth.EnvironmentVariableCredentialsProvider;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.syndicate.deployment.utils.ProjectUtils;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugin.logging.Log;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;
import org.apache.maven.project.MavenProject;

import java.io.File;
import java.util.Arrays;
import java.util.Objects;

import static com.syndicate.deployment.utils.ProjectUtils.SYNDICATE_BUILD_ID;

/**
 * Created by Oleksandr Onsha on 2019-08-12
 */
@Mojo(name = "publish-artifacts-to-s3", requiresDependencyResolution = ResolutionScope.RUNTIME)
public class PublishArtifactsToS3Goal extends AbstractMojo {

	@Parameter(defaultValue = "${project}", required = true, readonly = true)
	private MavenProject project;

	private Log logger;

	@Parameter(name = "bucketName", property = "maven.processor.bucketName", required = true)
	private String bucketName;

	@Parameter(name = "bucketRegion", property = "maven.processor.bucketRegion", required = true)
	private String bucketRegion;

	@Parameter(required = true)
	private String fileName;

	private AmazonS3 s3Client;

	public PublishArtifactsToS3Goal() {
		this.logger = getLog();
	}

	public MavenProject getProject() {
		return project;
	}

	public void setProject(MavenProject project) {
		this.project = project;
	}

	@Override
	public void execute() throws MojoExecutionException, MojoFailureException {
		String buildId = ProjectUtils.getPropertyFromRootProject(project, SYNDICATE_BUILD_ID);
		String projectTargetDir = ProjectUtils.getTargetFolderPath(project);
		File artifact = Arrays.stream(
			Objects.requireNonNull(new File(projectTargetDir).listFiles()))
			.filter(file -> file.getName().equals(fileName))
			.findAny().orElseGet(null);

		if (artifact != null) {
			logger.info(String.format("Uploading artifacts to %s/%s/%s", bucketName, buildId, fileName));
			getS3(bucketRegion).putObject(bucketName, String.format("%s/%s", buildId, fileName), artifact);
			logger.info("Artifact has been uploaded");
		}
	}

	private AmazonS3 getS3(String region) {
		if (this.s3Client == null) {
			s3Client = AmazonS3ClientBuilder.standard()
				.withCredentials(new EnvironmentVariableCredentialsProvider())
				.withRegion(Regions.fromName(region))
				.build();
		}
		return s3Client;
	}
}