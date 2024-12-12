package com.demodaggerformdatafileupload.handler.impl;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.demodaggerformdatafileupload.handler.EndpointHandler;
import com.google.gson.Gson;

import java.util.Map;

/**
 * Handler for not found endpoints.
 */
public class NotFoundHandler implements EndpointHandler {

    private final Gson gson;

    public NotFoundHandler(Gson gson) {
        this.gson = gson;
    }

    @Override
    public APIGatewayProxyResponseEvent handle(APIGatewayProxyRequestEvent requestEvent, Context context) {
        return new APIGatewayProxyResponseEvent()
                .withStatusCode(404)
                .withBody(gson.toJson(Map.of("message", "Not Found")));
    }
}
