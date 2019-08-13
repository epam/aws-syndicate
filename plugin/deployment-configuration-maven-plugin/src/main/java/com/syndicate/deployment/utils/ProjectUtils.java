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

	public static String getPropertyFromRootProject(MavenProject project, String propertyName) {
		MavenProject root = project.getParent();
		Object propertyValue;
		if (root != null) {
			while (root.getParent() != null) {
				root = root.getParent();
			}
			propertyValue = root.getProperties().get(propertyName);
		} else {
			propertyValue = project.getProperties().get(propertyName);
		}
		if (propertyValue != null) {
			return propertyValue.toString();
		}
		return null;
	}

	public static void setPropertyToRootProject(MavenProject project, String propertyName, String propertyValue) {
		MavenProject root = project.getParent();
		if (root != null) {
			while (root.getParent() != null) {
				root = root.getParent();
			}
			root.getProperties().setProperty(propertyName, propertyValue);
		} else {
			project.getProperties().setProperty(propertyName, propertyValue);
		}
	}
}
