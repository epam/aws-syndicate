const AWS = require('aws-sdk');

const cognitoIdentityServiceProvider = new AWS.CognitoIdentityServiceProvider({
    region: process.env.region // This uses the specified region or defaults to what's set in the AWS configuration
});

async function loginUser(email, password, userPoolId, clientId) {
    const params = {
        AuthFlow: 'ADMIN_USER_PASSWORD_AUTH',
        UserPoolId: userPoolId,
        ClientId: clientId,
        AuthParameters: {
            USERNAME: email,
            PASSWORD: password
        }
    };

    try {
        const data = await cognitoIdentityServiceProvider.adminInitiateAuth(params).promise();
        const idToken = data.AuthenticationResult.IdToken;
        return {
            statusCode: 200,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken: idToken })
        };
    } catch (error) {
        console.error(error);
        return {
            statusCode: 500,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Authentication failed", details: error.message })
        };
    }
}

async function signUpUser(email, password, userPoolId, clientId) {
    const params = {
        ClientId: clientId,
        Username: email,
        Password: password,
        UserAttributes: [{ Name: 'email', Value: email }]
    };

    try {
        const data = await cognitoIdentityServiceProvider.signUp(params).promise();
        const confirmParams = {
            Username: email,
            UserPoolId: userPoolId
        };

        const confirmedResult = await cognitoIdentityServiceProvider.adminConfirmSignUp(confirmParams).promise();
        return {
            statusCode: 200,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: 'OK' })
        };
    } catch (error) {
        console.error(error);
        return {
            statusCode: 500,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Signing up failed", details: error.message })
        };
    }
}

exports.handler = async (event) => {
    console.log(event);
    const body = JSON.parse(event.body);
    const userPoolId = process.env.CUPId;
    const clientId = process.env.CUPClientId;

    if (event.resource === '/login') {
        return loginUser(body.email, body.password, userPoolId, clientId);
    } else if (event.resource === '/signup') {
        return signUpUser(body.email, body.password, userPoolId, clientId);
    } else {
        // Handle unexpected resource paths
        return {
            statusCode: 400,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: "Invalid resource path" })
        };
    }
};