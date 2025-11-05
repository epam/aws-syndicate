package com.demodaggerformdatafileupload.handler.impl;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.demodaggerformdatafileupload.handler.EndpointHandler;

import java.util.Map;

/**
 * General handler that routes requests to the appropriate handler based on the HTTP method and path.
 */
public class GeneralHandler implements EndpointHandler {

    private final EndpointHandler notFoundHandler;
    private final Map<String, EndpointHandler> handlerMap;

    public GeneralHandler(EndpointHandler notFoundHandler, Map<String, EndpointHandler> handlerMap) {
        this.notFoundHandler = notFoundHandler;
        this.handlerMap = handlerMap;
    }

    @Override
    public APIGatewayProxyResponseEvent handle(APIGatewayProxyRequestEvent requestEvent, Context context) {
        // Construct the route key based on the HTTP method and path. This key is used to look up the appropriate handler.
        // For example, a GET request to /files would have a route key of "GET:/files".
        // The @IntoMap and @StringKey annotations in the HandlersModule.class should be used to define the route key for each handler.
        String routeKey = requestEvent.getHttpMethod() + ":" + requestEvent.getPath();

        return handlerMap.getOrDefault(routeKey, notFoundHandler).handle(requestEvent, context);
    }
}
