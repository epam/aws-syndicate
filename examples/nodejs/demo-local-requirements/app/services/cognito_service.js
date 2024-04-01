const AWS = require("aws-sdk");
const poolId = process.env.userpool_id;

class AuthenticationService {
    constructor() {
        this.cognitoIdentity = new AWS.CognitoIdentityServiceProvider({ region: process.env.region });
        this.clientId = undefined;
    }

    initializeClientId = async () => {
        const params = { UserPoolId: poolId, MaxResults: 1 };
        const data = await this.cognitoIdentity.listUserPoolClients(params).promise();

        if (data.UserPoolClients && data.UserPoolClients.length > 0) {
            this._clientId = data.UserPoolClients[0].ClientId;
        } else {
            throw new Error("Application Authentication Service is not configured properly.");
        }
    }

    async signUp(username, email, password) {
        const params = {
            ClientId: this.clientId,
            Username: username,
            Password: password,
            UserAttributes: [
                { Name: 'email', Value: email }
            ]
        };
        try {
            await this.cognitoIdentity.signUp(params).promise();
            const confirmParams = {
                Username: username,
                UserPoolId: this.userPoolId
            };
            const confirmedResult = await this.cognitoIdentity.adminConfirmSignUp(confirmParams).promise();
            return { signUpResult: confirmedResult };
        }
        catch (error) {
            console.log(`Failed to sign up: ${error}`);
            throw error;
        }
    }
}

module.exports = {AuthenticationService};