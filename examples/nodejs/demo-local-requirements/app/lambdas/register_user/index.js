const { AuthenticationService } = require("../../services/cognito_service");
const authService = new AuthenticationService();

// for local debugging
// import AWS from 'aws-sdk';
// var creds = new AWS.SharedIniFileCredentials({profile: 'default'});
// AWS.config.credentials = creds;
// AWS.config.update({ region: process.env.region });

// event example
// event = { "username": "John123", "password": "VerY_SeCurEd!0", "email": "John123@liamg.com" }
exports.handler = async (event) => {
    const { username, password, email } = event;
    try {
        await authService.signUp(username, email, password);
        return { message: `User ${email} was created` };
    }
    catch (error) {
        return { message: `Something went wrong when signing up: ${error}` };
    };
};
