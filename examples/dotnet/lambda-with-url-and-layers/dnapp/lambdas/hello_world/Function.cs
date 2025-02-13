using System.Collections.Generic;
using Amazon.Lambda.Core;
using Amazon.Lambda.APIGatewayEvents;

using System;
using HelloWorldLibrary;


[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.SystemTextJson.DefaultLambdaJsonSerializer))]

namespace SimpleLambdaFunction;


public class Function
{
    public APIGatewayProxyResponse FunctionHandler(APIGatewayProxyRequest request, ILambdaContext context)
    {
        string message = HelloWorld.GetMessage();
        return new APIGatewayProxyResponse
        {
            StatusCode = 200,
            Body = "Hello world from lambda! " + message,
            Headers = new Dictionary<string, string> { { "Content-Type", "text/plain" } }
        };
    }
}
