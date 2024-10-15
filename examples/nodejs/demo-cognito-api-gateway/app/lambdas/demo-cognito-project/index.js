const AWS = require('aws-sdk');

const cognitoIdentityServiceProvider = new AWS.CognitoIdentityServiceProvider({
    region: process.env.region // This uses the specified region or defaults to what's set in the AWS configuration
});

exports.handler = async (event) => {
    console.log(event);
    const body = JSON.parse(event.body);
    const userPoolId = process.env.CUPId;
    const clientId = process.env.CUPClientId;

    if (event.resource === '/login') {
        const params = {
            AuthFlow: 'ADMIN_USER_PASSWORD_AUTH',
            UserPoolId: userPoolId,
            ClientId: clientId,
            AuthParameters: {
                USERNAME: body.email,
                PASSWORD: body.password
            }
        };

        try {
            const data = await cognitoIdentityServiceProvider.adminInitiateAuth(params).promise();
            const idToken = data.AuthenticationResult.IdToken;
            return {
                statusCode: 200,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ idToken: idToken })
            };
        } catch (error) {
            console.error(error);
            return {
                statusCode: 500,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ error: "Authentication failed", details: error.message })
            };
        }
    } else if (event.resource === '/signup') {
        const params = {
            ClientId: clientId,
            Username: body.email,
            Password: body.password,
            UserAttributes: [{ Name: 'email', Value: body.email }]
        };

        try {
            const data = await cognitoIdentityServiceProvider.signUp(params).promise();
            const confirmParams = {
                Username: body.email,
                UserPoolId: userPoolId
            };

            const confirmedResult = await cognitoIdentityServiceProvider.adminConfirmSignUp(confirmParams).promise();
            return {
                statusCode: 200,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: 'OK' })
            };
        } catch (error) {
            console.error(error);
            return {
                statusCode: 500,
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ error: "Signing up failed", details: error.message })
            };
        }
    } else {
        // Handle unexpected resource paths
        return {
            statusCode: 400,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ error: "Invalid resource path" })
        };
    }
};