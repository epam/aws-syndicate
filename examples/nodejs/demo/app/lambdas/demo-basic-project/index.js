const { v4: uuidv4 } = require("uuid");
const AWS = require("aws-sdk");

const docClient = new AWS.DynamoDB.DocumentClient();
const tableName = "Users"

// event example
// event = { "username": "John123" }
exports.handler = async (event) => {
	const params = {
		TableName: tableName,
		Item: {
			"id": uuidv4(),
			"username": event.username,
			"registrationDate": new Date().toISOString()
		}
	};
	try {
		const data = await docClient.put(params).promise();
		return params.Item;
	} catch (err) {
		return JSON.stringify(err, null, 2);
	}
};