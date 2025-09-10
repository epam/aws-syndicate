/*
 * Copyright 2018 EPAM Systems, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.syndicate.deployment.annotations.lambda;

import com.syndicate.deployment.annotations.DeploymentResource;
import com.syndicate.deployment.model.Architecture;
import com.syndicate.deployment.model.ArtifactExtension;
import com.syndicate.deployment.model.DeploymentRuntime;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Annotation for defining AWS Lambda layers.
 * <p>
 * Lambda layers provide a convenient way to package libraries, custom runtimes, or other function
 * dependencies that can be shared across multiple Lambda functions. Layers help reduce deployment
 * package sizes and promote code reuse.
 * </p>
 *
 * <h2>Usage Example:</h2>
 * <pre>{@code
 * @LambdaLayer(
 *     layerName = "my-custom-libs",
 *     description = "Custom libraries layer",
 *     libraries = {"lib/gson-2.10.1.jar", "lib/commons-lang3-3.12.0.jar"},
 *     runtime = DeploymentRuntime.JAVA11,
 *     architectures = {Architecture.X86_64}
 * )
 * public class MyCustomLayer {
 * }
 * }</pre>
 *
 * <h2>Custom Libraries Integration:</h2>
 * <p>
 * The {@code libraries} parameter allows you to include custom JAR files that are not available
 * in Maven Central. These libraries should be placed in your project directory and referenced
 * by their relative paths.
 * </p>
 *
 * <p>
 * To use custom libraries in your Maven project, you can declare them as system dependencies:
 * </p>
 * <pre>{@code
 * <dependency>
 *     <groupId>demo.custom.sdk</groupId>
 *     <artifactId>gson-downloaded-library</artifactId>
 *     <version>2.10.1</version>
 *     <scope>system</scope>
 *     <systemPath>${basedir}/lib/gson-2.10.1.jar</systemPath>
 * </dependency>
 * }</pre>
 *
 * @see <a href="https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html">AWS Lambda Layers</a>
 * @author Oleksandr Onsha
 * @since 2019-11-29
 */
@DeploymentResource
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface LambdaLayer {

	/**
	 * The name of the Lambda layer.
	 * <p>
	 * Layer names must be unique within your AWS account and region. The name can contain
	 * letters, numbers, hyphens, and underscores, and must be between 1 and 140 characters.
	 * </p>
	 *
	 * @return the layer name
	 */
	String layerName();

	/**
	 * A description of the layer.
	 * <p>
	 * Provides additional information about the layer's purpose and contents.
	 * Maximum length is 256 characters.
	 * </p>
	 *
	 * @return the layer description, empty string by default
	 */
	String description() default  "";

	/**
	 * The filename for the layer artifact.
	 * <p>
	 * If not specified, the layer name will be used as the filename.
	 * </p>
	 *
	 * @return the layer filename, empty string by default
	 */
	String layerFileName() default "";

	/**
	 * An array of library file paths to include in the layer.
	 * <p>
	 * Specify relative paths to JAR files or other library files within your project.
	 * These files will be packaged into the layer and made available to Lambda functions
	 * that use this layer.
	 * </p>
	 *
	 * <h4>Examples:</h4>
	 * <ul>
	 *   <li>{@code "lib/gson-2.10.1.jar"} - Single custom library</li>
	 *   <li>{@code {"lib/gson-2.10.1.jar", "lib/commons-lang3-3.12.0.jar"}} - Multiple libraries</li>
	 *   <li>{@code "dependencies/"} - Include all files from a directory</li>
	 * </ul>
	 *
	 * <p>
	 * For Maven projects, these libraries can be declared as system dependencies to ensure
	 * proper compilation while keeping them separate from Maven Central dependencies.
	 * </p>
	 *
	 * @return array of library file paths, empty array by default
	 */
	String[] libraries() default {};

	/**
	 * The license information for the layer.
	 * <p>
	 * Specify license details for the libraries and code included in the layer.
	 * This is particularly important when distributing layers with third-party libraries.
	 * </p>
	 *
	 * @return the license information, empty string by default
	 */
	String licence() default "";

	/**
	 * The artifact extension for the layer package.
	 * <p>
	 * Determines the format of the layer package. ZIP is the most common format
	 * for Lambda layers and is supported by all runtimes.
	 * </p>
	 *
	 * @return the artifact extension, ZIP by default
	 */
	ArtifactExtension artifactExtension() default ArtifactExtension.ZIP;

	/**
	 * The runtime environment for the layer.
	 * <p>
	 * Specifies the Lambda runtime that this layer is compatible with.
	 * Layers are runtime-specific, so choose the appropriate runtime for your use case.
	 * </p>
	 *
	 * @return the deployment runtime, JAVA11 by default
	 */
	DeploymentRuntime runtime() default DeploymentRuntime.JAVA11;

	/**
	 * The processor architectures supported by this layer.
	 * <p>
	 * Lambda supports both x86_64 and arm64 architectures. Specify the architectures
	 * that your layer supports. If not specified, the layer will support the default
	 * architecture for your account.
	 * </p>
	 *
	 * @return array of supported architectures, empty array by default
	 */
	Architecture[] architectures() default {};

}
