package com.syndicate.deployment.processor.impl;

import com.syndicate.deployment.annotations.lambda.LambdaLayer;
import com.syndicate.deployment.factories.LayerConfigurationFactory;
import com.syndicate.deployment.model.LayerConfiguration;
import com.syndicate.deployment.model.Pair;
import com.syndicate.deployment.processor.AbstractAnnotationProcessor;
import com.syndicate.deployment.processor.IAnnotationProcessor;
import com.syndicate.deployment.resolvers.reflection.ReflectionsHolder;

import java.util.Collection;

/**
 * Created by Oleksandr Onsha on 2019-12-02
 */
public class LayerAnnotationProcessor extends AbstractAnnotationProcessor<LayerConfiguration> implements IAnnotationProcessor<LayerConfiguration> {


    @Override
    protected Pair<String, LayerConfiguration> process(Class<?> sourceClass, String version, String fileName, String path) {
        LambdaLayer layerDef = sourceClass.getAnnotation(LambdaLayer.class);
        LayerConfiguration configuration = LayerConfigurationFactory.createLayerConfiguration(layerDef);
        return new Pair<>(configuration.getName(), configuration);
    }

    @Override
    public Collection<Class<?>> getAnnotatedClasses(String[] packages) {
        return ReflectionsHolder.getTypesAnnotatedWith(packages, LambdaLayer.class);
    }
}
