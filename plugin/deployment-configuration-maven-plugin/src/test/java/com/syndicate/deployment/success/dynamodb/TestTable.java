package com.syndicate.deployment.success.dynamodb;

import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBAttribute;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBHashKey;
import com.amazonaws.services.dynamodbv2.datamodeling.DynamoDBTable;

import java.util.List;

@DynamoDBTable(tableName = "TestTable")
public class TestTable {

    @DynamoDBHashKey(attributeName = "hash")
    private String hashKey;

    @DynamoDBAttribute(attributeName = "someField")
    private List<String> field;

}
