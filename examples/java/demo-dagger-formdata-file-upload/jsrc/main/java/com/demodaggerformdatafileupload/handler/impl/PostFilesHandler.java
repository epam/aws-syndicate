package com.demodaggerformdatafileupload.handler.impl;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.demodaggerformdatafileupload.dto.FileData;
import com.demodaggerformdatafileupload.dto.FileResponse;
import com.demodaggerformdatafileupload.dto.formdata.FormDataV1;
import com.demodaggerformdatafileupload.dto.formdata.input.FileInput;
import com.demodaggerformdatafileupload.dto.formdata.input.TextInput;
import com.demodaggerformdatafileupload.dto.formdata.input.InputType;
import com.demodaggerformdatafileupload.exception.ProcessFormDataException;
import com.demodaggerformdatafileupload.handler.EndpointHandler;
import com.demodaggerformdatafileupload.utils.DataMapper;
import com.demodaggerformdatafileupload.service.FileStoreService;
import com.demodaggerformdatafileupload.utils.MultipartParser;
import com.google.gson.Gson;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Handler for POST /files endpoint. Uploads files to file storage and returns their URLs.
 * works with multipart/form-data requests only.
 */
public class PostFilesHandler implements EndpointHandler {

    private final FileStoreService fileStoreService;
    private final MultipartParser multipartParser;
    private final Gson gson;

    public PostFilesHandler(FileStoreService fileStoreService, MultipartParser multipartParser, Gson gson) {
        this.fileStoreService = fileStoreService;
        this.multipartParser = multipartParser;
        this.gson = gson;
    }

    @Override
    public APIGatewayProxyResponseEvent handle(APIGatewayProxyRequestEvent requestEvent, Context context) {
        try {
            // Check if Content-Type header is present and is multipart/form-data
            String contentType = requestEvent.getHeaders().get("content-type");
            if (contentType == null) {
                throw new ProcessFormDataException("Content-Type header is missing");
            }
            if (!contentType.startsWith("multipart/form-data")) {
                throw new ProcessFormDataException("Invalid Content-Type header. Expected multipart/form-data");
            }

            // Parse request body and map it to the FormData object
            FormDataV1 formData = DataMapper
                    .mapMultipartParserResultToFormDataV1(multipartParser.parse(requestEvent.getBody(), contentType));

            // Get metadata from the FormData using all text inputs as metadata
            Map<String, String> metadata = formData.getInputs().stream()
                    .filter(input -> input.getInputType() == InputType.TEXT)
                    .map(TextInput.class::cast)
                    .collect(HashMap::new, (map, input) -> map.put(input.getName(), input.getValue()), Map::putAll);

            // Get all files from the FormData object
            List<FileData> files = formData.getInputs().stream()
                    .filter(input -> input.getInputType() == InputType.FILE)
                    .map(FileInput.class::cast)
                    .map(FileInput::getValue)
                    .flatMap(List::stream)
                    .toList();

            // Upload files to file storage
            List<String> fileUrls = files.stream()
                    .map(fileData -> fileStoreService.upload(fileData, metadata))
                    .toList();

            // return URLs of uploaded files
            return new APIGatewayProxyResponseEvent()
                    .withStatusCode(200)
                    .withBody(gson.toJson(new FileResponse(fileUrls)));
        } catch (ProcessFormDataException e) {
            return new APIGatewayProxyResponseEvent()
                    .withStatusCode(400)
                    .withBody(gson.toJson(Map.of("error", e.getMessage())));
        }

    }
}
