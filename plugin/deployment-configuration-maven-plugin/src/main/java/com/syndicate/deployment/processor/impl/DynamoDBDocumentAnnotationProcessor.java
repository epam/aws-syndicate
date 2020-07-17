package com.syndicate.deployment.processor.impl;

import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBAttribute;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBHashKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBIndexHashKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBIndexRangeKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBRangeKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBTable;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBVersionAttribute;
import com.syndicate.deployment.model.JsonSchema;
import com.syndicate.deployment.model.JsonType;
import com.syndicate.deployment.model.Pair;
import com.syndicate.deployment.processor.AbstractAnnotationProcessor;
import com.syndicate.deployment.processor.IAnnotationProcessor;
import com.syndicate.deployment.resolvers.reflection.AttributeNameChainedResolver;
import com.syndicate.deployment.resolvers.reflection.IChainedResolver;
import org.apache.maven.plugin.MojoExecutionException;
import org.reflections.Reflections;

import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

public class DynamoDBDocumentAnnotationProcessor extends AbstractAnnotationProcessor<JsonSchema> implements IAnnotationProcessor<JsonSchema> {

    private final Map<JsonType, List<Class<?>>> typeMapping = new HashMap<>();

    private IChainedResolver<Field, String> chainedResolver;


    public DynamoDBDocumentAnnotationProcessor() {
        this.chainedResolver = new AttributeNameChainedResolver(Arrays.asList(
                DynamoDBHashKey.class, DynamoDBIndexHashKey.class,
                DynamoDBAttribute.class, DynamoDBRangeKey.class,
                DynamoDBVersionAttribute.class, DynamoDBIndexRangeKey.class));
    }

    {
        typeMapping.put(JsonType.LIST, Arrays.asList(Enum.class, List.class, Set.class));
        typeMapping.put(JsonType.BOOL, Arrays.asList(boolean.class, Boolean.class));
        typeMapping.put(JsonType.NUMBER, Arrays.asList(byte.class, Byte.class, short.class,
                Short.class, long.class, Long.class,
                float.class, Float.class, double.class, Double.class));
        typeMapping.put(JsonType.INTEGER, Arrays.asList(int.class, Integer.class));
        typeMapping.put(JsonType.OBJECT, Collections.singletonList(Map.class));
        typeMapping.put(JsonType.STRING, Collections.singletonList(String.class));
    }

    @Override
    protected Pair<String, JsonSchema> process(Class<?> sourceClass, String version, String fileName, String path) throws MojoExecutionException {
        DynamoDBTable annotation = sourceClass.getAnnotation(DynamoDBTable.class);
        Field[] declaredFields = sourceClass.getDeclaredFields();
        List<Field> nonStaticFields = Arrays.stream(declaredFields)
                .filter(field -> !Modifier.isStatic(field.getModifiers()))
                .collect(Collectors.toList());
        JsonSchema jsonSchema = new JsonSchema();
        jsonSchema.setClassName(sourceClass.getName());
        for (Field field : nonStaticFields) {
            String fieldSchemaName = resolveFieldSchemaName(field);
            JsonType fieldSchemaType = resolveFieldSchemaType(field);
            jsonSchema.addProperty(fieldSchemaName, fieldSchemaType.getTypeName());
        }
        return new Pair<>(annotation.tableName(), jsonSchema);
    }

    @Override
    protected List<Class<?>> getAnnotatedClasses(String[] packages) {
        List<Class<?>> dynamoDbTablesClasses = new ArrayList<>();
        for (String nestedPackage : packages) {
            dynamoDbTablesClasses.addAll(new Reflections(nestedPackage).getTypesAnnotatedWith(DynamoDBTable.class));
        }

        List<Class<?>> directTableClasses = new ArrayList<>();
        for (Class<?> dynamoDbClass : dynamoDbTablesClasses) {
            List<Annotation> declaredAnnotations = Arrays.asList(dynamoDbClass.getDeclaredAnnotations());
            if (declaredAnnotations.stream().anyMatch(annotation -> annotation.annotationType() == DynamoDBTable.class)) {
                directTableClasses.add(dynamoDbClass);
            }
        }
        return directTableClasses;
    }

    private String resolveFieldSchemaName(Field field) throws MojoExecutionException {
        String resolve = chainedResolver.resolve(field);
        return resolve != null ? resolve : field.getName();
    }

    // todo extend with Class-types fields processing
    private JsonType resolveFieldSchemaType(Field field) {
        for (Map.Entry<JsonType, List<Class<?>>> entry : typeMapping.entrySet()) {
            if (entry.getValue().contains(field.getType())) {
                return entry.getKey();
            }
        }
        return JsonType.OBJECT;
    }
}
