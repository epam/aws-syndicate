package com.syndicate.deployment.success.dynamodb;

import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBAttribute;

import java.util.Map;

public class TestTableChild extends TestTable {

    @DynamoDBAttribute(attributeName = "additionalField")
    private Map<String, String> someAdditionalField;

}
