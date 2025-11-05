using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using Amazon.CognitoIdentityProvider;
using Amazon.CognitoIdentityProvider.Model;
using Amazon.Lambda.APIGatewayEvents;
using Amazon.Lambda.Core;

[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.SystemTextJson.DefaultLambdaJsonSerializer))]

namespace SimpleLambdaFunction
{
    public class Function
    {
        private readonly ApiHandler _apiHandler;

        public Function()
        {
            _apiHandler = new ApiHandler();
        }

        public async Task<APIGatewayProxyResponse> FunctionHandler(APIGatewayProxyRequest request,
            ILambdaContext context)
        {
            return await _apiHandler.HandleRequest(request, context);
        }
    }

    public class ApiHandler
    {
        private readonly AuthenticationService _authService;

        public ApiHandler()
        {
            _authService = new AuthenticationService();
        }

        public async Task<APIGatewayProxyResponse> HandleRequest(APIGatewayProxyRequest eventRequest,
            ILambdaContext context)
        {
            Console.WriteLine(JsonSerializer.Serialize(eventRequest));

            var requestPath = eventRequest.Resource;
            var methodName = eventRequest.HttpMethod;

            var actionEndpointMapping =
                new Dictionary<string,
                    Dictionary<string, Func<APIGatewayProxyRequest, Task<APIGatewayProxyResponse>>>>()
                {
                    {
                        "/signup", new Dictionary<string, Func<APIGatewayProxyRequest, Task<APIGatewayProxyResponse>>>
                        {
                            { "POST", Signup }
                        }
                    },
                    {
                        "/signin", new Dictionary<string, Func<APIGatewayProxyRequest, Task<APIGatewayProxyResponse>>>
                        {
                            { "POST", Signin }
                        }
                    }
                };

            if (!actionEndpointMapping.TryGetValue(requestPath, out var resourceMethods) ||
                !resourceMethods.TryGetValue(methodName, out var action))
            {
                return InvalidEndpoint(requestPath, methodName);
            }

            if (!string.IsNullOrEmpty(eventRequest.Body))
            {
                eventRequest.Body = eventRequest.Body.Trim();
            }

            return await action(eventRequest);
        }

        private APIGatewayProxyResponse InvalidEndpoint(string path, string method)
        {
            return FormatResponse(400,
                new
                {
                    message = $"Bad request syntax or unsupported method. Request path: {path}. HTTP method: {method}"
                });
        }

        private APIGatewayProxyResponse FormatResponse(int code, object response)
        {
            var responseString = JsonSerializer.Serialize(response);
            Console.WriteLine(responseString);

            return new APIGatewayProxyResponse
            {
                StatusCode = code,
                Headers = new Dictionary<string, string> { { "Content-Type", "application/json" } },
                Body = responseString
            };
        }

        private List<string> ValidateRequestParams(string[] expected, Dictionary<string, JsonElement> received)
        {
            var missing = new List<string>();
            foreach (var param in expected)
            {
                if (!received.ContainsKey(param))
                {
                    missing.Add(param);
                }
            }

            return missing;
        }

        private async Task<APIGatewayProxyResponse> Signup(APIGatewayProxyRequest request)
        {
            var body = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(request.Body ?? "{}",
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

            var requiredParams = new[] { "firstName", "lastName", "email", "password" };
            var missingParams = ValidateRequestParams(requiredParams, body);

            if (missingParams.Count > 0)
            {
                return FormatResponse(400,
                    new { message = $"Missing required parameters: {string.Join(", ", missingParams)}" });
            }

            var firstName = body["firstName"].GetString();
            var lastName = body["lastName"].GetString();
            var email = body["email"].GetString();
            var password = body["password"].GetString();

            try
            {
                await _authService.SignUp(firstName, lastName, email, password);
                return FormatResponse(200, new { message = $"User {email} was created" });
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex);
                return FormatResponse(400, new { message = $"Something went wrong when signing up: {ex.Message}" });
            }
        }

        private async Task<APIGatewayProxyResponse> Signin(APIGatewayProxyRequest request)
        {
            var body = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(request.Body ?? "{}",
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

            var requiredParams = new[] { "email", "password" };
            var missingParams = ValidateRequestParams(requiredParams, body);

            if (missingParams.Count > 0)
            {
                return FormatResponse(400,
                    new { message = $"Missing required parameters: {string.Join(", ", missingParams)}" });
            }

            var email = body["email"].GetString();
            var password = body["password"].GetString();

            try
            {
                var result = await _authService.SignIn(email, password);
                return FormatResponse(200, new { accessToken = result });
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex);
                return FormatResponse(400,
                    new
                    {
                        message =
                            "We encountered an issue while trying to log you in. Please try again in a few minutes."
                    });
            }
        }

        public class AuthenticationService
        {
            private readonly AmazonCognitoIdentityProviderClient _cognitoClient;
            private readonly string? _clientId = Environment.GetEnvironmentVariable("cup_client_id");
            private readonly string? _userPollId = Environment.GetEnvironmentVariable("cup_id");

            public AuthenticationService()
            {
                _cognitoClient = new AmazonCognitoIdentityProviderClient();
            }

            public async Task SignUp(string firstName, string lastName, string email, string password)
            {
                var signUpRequest = new SignUpRequest
                {
                    ClientId = _clientId,
                    Username = email,
                    Password = password,
                    UserAttributes = new List<AttributeType>
                    {
                        new AttributeType { Name = "given_name", Value = firstName },
                        new AttributeType { Name = "family_name", Value = lastName },
                        new AttributeType { Name = "email", Value = email }
                    }
                };

                await _cognitoClient.SignUpAsync(signUpRequest);

                var confirmRequest = new AdminConfirmSignUpRequest
                {
                    UserPoolId = _userPollId,
                    Username = email
                };

                await _cognitoClient.AdminConfirmSignUpAsync(confirmRequest);
            }

            public async Task<string> SignIn(string email, string password)
            {
                var authRequest = new AdminInitiateAuthRequest
                {
                    AuthFlow = AuthFlowType.ADMIN_NO_SRP_AUTH,
                    ClientId = _clientId,
                    UserPoolId = _userPollId,
                    AuthParameters = new Dictionary<string, string>
                    {
                        { "USERNAME", email },
                        { "PASSWORD", password }
                    }
                };

                try
                {
                    var authResponse = await _cognitoClient.AdminInitiateAuthAsync(authRequest);
                    return authResponse.AuthenticationResult.IdToken;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to log in: {ex}");
                    throw;
                }
            }
        }
    }
}