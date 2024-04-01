const lodash = require("lodash");
const AWS = require("aws-sdk");
const s3 = new AWS.S3();

// event example
// event = { "key": "key_1233512.json", "data": [1, 2,3, 4, 5, 6, 7, 8] }
exports.handler = async (event) => {
    let chunks = _.chunk(event.data, 2);
	const params = {
		Bucket: process.env.bucket_name,
		Key: event.key,
		Body: JSON.stringify(chunks, null, 2)
	};

    await s3.putObject(params).promise()
        .then(data => console.log(data))
        .catch(err => console.log(err, err.stack));
};
