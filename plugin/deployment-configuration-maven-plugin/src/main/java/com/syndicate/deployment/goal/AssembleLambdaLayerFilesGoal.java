package com.syndicate.deployment.goal;

import com.syndicate.deployment.model.LayerConfiguration;
import com.syndicate.deployment.processor.IAnnotationProcessor;
import com.syndicate.deployment.processor.impl.LayerAnnotationProcessor;
import com.syndicate.deployment.utils.ProjectUtils;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.ResolutionScope;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Map;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static com.syndicate.deployment.utils.ProjectUtils.getRootDirPath;

@Mojo(name = "assemble-lambda-layer-files", requiresDependencyResolution = ResolutionScope.RUNTIME, threadSafe = true)
public class AssembleLambdaLayerFilesGoal extends AbstractMetaGoal {

    private static final String AWS_LAMBDA_LAYER_FILE_ZIP_ARCHIVE_INTERNAL_PATH = "java/lib/";
    private final IAnnotationProcessor<LayerConfiguration> layerAnnotationProcessor;

    public AssembleLambdaLayerFilesGoal() {
        this.layerAnnotationProcessor = new LayerAnnotationProcessor();
    }

    @Override
    public void executeGoal(String absolutePath) throws MojoExecutionException {
        AssembleLambdaLayerFilesAndWriteToTargetFolder(getLayerConfigurations(absolutePath));
    }

    protected Map<String, LayerConfiguration> getLayerConfigurations(String absolutePath) throws MojoExecutionException {
        return layerAnnotationProcessor.generateMeta(absolutePath, packages, project.getVersion(), fileName);
    }

    protected void AssembleLambdaLayerFilesAndWriteToTargetFolder(Map<String, LayerConfiguration> layerConfigurationsByLayerName) {
        if (layerConfigurationsByLayerName == null || layerConfigurationsByLayerName.isEmpty()) {
            return;
        }
        logger.info("Starting creating layers' assembled files...");
        String rootPath = getRootDirPath(project);
        String targetPath = ProjectUtils.getTargetFolderPath(project);
        layerConfigurationsByLayerName.forEach((layerName, layerConfig) ->
                {
                    try {
                        String[] layerLibraries = layerConfig.getLibraries();
                        if (layerLibraries.length < 1) {
                            logger.warn(String.format("Layer '%s' has no any library to add to assembled file, skipping...", layerName));
                            return;
                        }
                        String targetFileName = layerConfig.getDeploymentPackage();
                        writeLibrariesIntoOneZipFile(
                                rootPath,
                                layerLibraries,
                                targetPath,
                                targetFileName,
                                AWS_LAMBDA_LAYER_FILE_ZIP_ARCHIVE_INTERNAL_PATH
                        );
                    } catch (Exception e) {
                        logger.error(String.format("Cannot create and write zip file for layer '%s'. Reason: %s", layerName, e.getMessage()));
                    }
                }
        );
    }

    protected void writeLibrariesIntoOneZipFile(String rootPath, String[] libraries, String targetPath, String targetFileName, String internalZipArchivePath) {
        File targetFile = new File(targetPath, targetFileName);
        try (FileOutputStream fos = new FileOutputStream(targetFile); ZipOutputStream zos = new ZipOutputStream(fos)) {
            Stream.of(libraries).forEach(libraryFileNameWithRelativePath -> {
                File sourceFile = new File(rootPath, libraryFileNameWithRelativePath);
                try (FileInputStream fis = new FileInputStream(sourceFile)) {
                    String[] libraryFileNameTokens = libraryFileNameWithRelativePath.split("[\\\\|/]");
                    String filename = libraryFileNameTokens[libraryFileNameTokens.length - 1];
                    String internalFileName = internalZipArchivePath + filename;
                    ZipEntry zipEntry = new ZipEntry(internalFileName);
                    zos.putNextEntry(zipEntry);

                    byte[] buffer = new byte[1024];
                    int length;
                    while ((length = fis.read(buffer)) > 0) {
                        zos.write(buffer, 0, length);
                    }
                } catch (IOException e) {
                    throw new RuntimeException(e.getMessage());
                }
            });
        } catch (IOException e) {
            throw new RuntimeException(e.getMessage());
        }
    }
}
