package com.syndicate.deployment.resolvers.reflection;

import com.amazonaws.util.StringUtils;
import org.apache.maven.plugin.MojoExecutionException;

import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

public class AttributeNameChainedResolver implements IChainedResolver<Field, String> {

    private List<Class<? extends Annotation>> annotationsList;

    public AttributeNameChainedResolver(List<Class<? extends Annotation>> annotationsList) {
        this.annotationsList = annotationsList;
    }


    @Override
    public String resolve(Field payload) throws MojoExecutionException {
        for (Class<? extends Annotation> annotation : this.annotationsList) {
            String attributeNameValue = this.getAttributeValueFromAnnotation(payload, annotation);
            if (!StringUtils.isNullOrEmpty(attributeNameValue)) {
                return attributeNameValue;
            }
        }
        return null;
    }

    private <T extends Annotation> String getAttributeValueFromAnnotation(Field field, Class<T> annotation) throws MojoExecutionException {
        try {
            T[] declaredAnnotationsByType = field.getDeclaredAnnotationsByType(annotation);
            Optional<T> targetAnnotation = Stream.of(declaredAnnotationsByType).findFirst();
            if (targetAnnotation.isPresent()) {
                Method[] declaredMethods = targetAnnotation.get().getClass().getDeclaredMethods();
                Optional<Method> attributeNameOpt = Stream.of(declaredMethods)
                        .filter(method -> method.getName().equalsIgnoreCase("attributeName"))
                        .findFirst();
                if (attributeNameOpt.isPresent()) {
                    Object attributeNameValue = attributeNameOpt.get().invoke(targetAnnotation.get());
                    return (String) attributeNameValue;
                }
            }
        } catch (IllegalAccessException | InvocationTargetException e) {
            throw new MojoExecutionException(String.format("Error occurred while extracting attributeName from annotation %s", annotation.getName()), e);
        }
        return null;
    }
}
