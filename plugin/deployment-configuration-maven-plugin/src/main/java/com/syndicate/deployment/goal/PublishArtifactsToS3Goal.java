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

	@Parameter(name = "bucketName", property = "maven.processor.bucketName")
	private String bucketName;

	@Parameter(name = "bucketRegion", property = "maven.processor.bucketRegion")
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
		if (bucketName == null || bucketRegion == null) {
			logger.debug("Properties bucketName and bucketProperties are not set. " +
				"Skipping artifacts upload to s3");
			return;
		}
		String buildId = ProjectUtils.getPropertyFromRootProject(project, SYNDICATE_BUILD_ID);
		String projectTargetDir = ProjectUtils.getTargetFolderPath(project);
		File[] obj = new File(projectTargetDir).listFiles();
		File artifact = Arrays.stream(
			Objects.requireNonNull(obj))
			.filter(file -> file.getName().contains(fileName))
			.findAny().orElse(null);

		if (artifact != null) {
			logger.info(String.format("Uploading artifacts to %s/%s/%s", bucketName, buildId, artifact.getName()));
			getS3(bucketRegion).putObject(bucketName, String.format("%s/%s", buildId, artifact.getName()), artifact);
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