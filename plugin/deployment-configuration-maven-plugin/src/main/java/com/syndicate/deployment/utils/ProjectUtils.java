package com.syndicate.deployment.utils;

import org.apache.maven.project.MavenProject;

import java.io.File;

/**
 * Created by Oleksandr Onsha on 2019-08-12
 */
public final class ProjectUtils {

	public static final String SYNDICATE_BUILD_ID = "syndicate-build-id";
	private static final String MAVEN_TARGET_FOLDER_NAME = "target";

	public static String getTargetFolderPath(MavenProject project) {
		return project.getBasedir().getAbsolutePath() + File.separator + MAVEN_TARGET_FOLDER_NAME;
	}

	public static String getRootDirPath(MavenProject project) {
		return getRootProject(project).getBasedir().getAbsolutePath();
	}

	public static String getPropertyFromRootProject(MavenProject project, String propertyName) {
		Object propertyValue = getRootProject(project).getProperties().getProperty(propertyName);
		if (propertyValue != null) {
			return propertyValue.toString();
		}
		return null;
	}

	public static void setPropertyToRootProject(MavenProject project, String propertyName, String propertyValue) {
		getRootProject(project).getProperties().setProperty(propertyName, propertyValue);
	}

	private static MavenProject getRootProject(MavenProject project) {
		MavenProject root = project.getParent();
		if (root != null) {
			while (root.getParent() != null) {
				root = root.getParent();
			}
		}
		return root;
	}
}
