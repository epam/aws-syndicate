package com.demodaggerformdatafileupload.handler.impl;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.demodaggerformdatafileupload.dto.FileResponse;
import com.demodaggerformdatafileupload.handler.EndpointHandler;
import com.demodaggerformdatafileupload.service.FileStoreService;
import com.google.gson.Gson;

import java.util.List;

/**
 * Handler for GET /files endpoint. Returns urls of all files stored in the system.
 */
public class GetFilesHandler implements EndpointHandler {

    private final Gson gson;
    private final FileStoreService fileStoreService;

    public GetFilesHandler(FileStoreService fileStoreService, Gson gson) {
        this.fileStoreService = fileStoreService;
        this.gson = gson;
    }

    @Override
    public APIGatewayProxyResponseEvent handle(APIGatewayProxyRequestEvent requestEvent, Context context) {
        List<String> fileUrls = fileStoreService.getAll();
        return new APIGatewayProxyResponseEvent()
                .withStatusCode(200)
                .withBody(gson.toJson(new FileResponse(fileUrls)));
    }
}