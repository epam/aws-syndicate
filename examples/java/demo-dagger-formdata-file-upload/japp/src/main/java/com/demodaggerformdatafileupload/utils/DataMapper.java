package com.demodaggerformdatafileupload.utils;

import com.demodaggerformdatafileupload.dto.FileData;
import com.demodaggerformdatafileupload.dto.formdata.FormDataV1;
import com.demodaggerformdatafileupload.dto.formdata.FormDataV2;
import com.demodaggerformdatafileupload.dto.formdata.input.FileInput;
import com.demodaggerformdatafileupload.dto.formdata.input.Input;
import com.demodaggerformdatafileupload.dto.formdata.input.TextInput;
import com.demodaggerformdatafileupload.dto.formdata.FrontendDemoExampleFormData;
import org.apache.commons.fileupload.FileItem;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class DataMapper {

    private DataMapper() {
        throw new UnsupportedOperationException("Utility class");
    }

    public static FormDataV1 mapMultipartParserResultToFormDataV1(Map<String, List<FileItem>> parsedData) {
        List<Input> inputs = new ArrayList<>();

        for (Map.Entry<String, List<FileItem>> entry : parsedData.entrySet()) {
            String name = entry.getKey();
            List<FileItem> fileItems = entry.getValue();

            if (fileItems.isEmpty()) {
                continue;
            }

            if (fileItems.get(0).isFormField()) {
                // Text input
                String value = fileItems.get(0).getString();
                inputs.add(new TextInput(name, value));
            } else {
                // File input
                List<FileData> fileDataList = fileItems.stream()
                        .map(fileItem -> new FileData(fileItem.getName(), fileItem.getContentType(), fileItem.get()))
                        .toList();
                inputs.add(new FileInput(name, fileDataList));
            }
        }

        return new FormDataV1(inputs);
    }

    public static FormDataV2 mapMultipartParserResultToFormDataV2(Map<String, List<FileItem>> parsedData) {
        Map<String, String> fields = new HashMap<>();
        Map<String, List<FileData>> files = new HashMap<>();

        for (FileItem item : parsedData.values().stream().flatMap(List::stream).toList()) {
            if (item.isFormField()) {
                fields.put(item.getFieldName(), item.getString());
            } else {
                FileData fileData = new FileData(
                        item.getName(),
                        item.getContentType(),
                        item.get()
                );
                files.computeIfAbsent(item.getFieldName(), k -> new ArrayList<>()).add(fileData);
            }
        }

        return new FormDataV2(fields, files);

    }

    public static FormDataV2 mapFormDataV1toFormDataV2(FormDataV1 formDataV1) {
        Map<String, String> fields = new HashMap<>();
        Map<String, List<FileData>> files = new HashMap<>();

        for (Input input : formDataV1.getInputs()) {
            if (input instanceof TextInput textInput) {
                fields.put(textInput.getName(), textInput.getValue());
            } else if (input instanceof FileInput fileInput) {
                files.put(fileInput.getName(), fileInput.getValue());
            }
        }

        return new FormDataV2(fields, files);
    }

    public static FormDataV1 mapFormDataV2toFormDataV1(FormDataV2 formDataV2) {
        List<Input> inputs = new ArrayList<>();

        for (Map.Entry<String, String> entry : formDataV2.getFields().entrySet()) {
            inputs.add(new TextInput(entry.getKey(), entry.getValue()));
        }

        for (Map.Entry<String, List<FileData>> entry : formDataV2.getFiles().entrySet()) {
            inputs.add(new FileInput(entry.getKey(), entry.getValue()));
        }

        return new FormDataV1(inputs);
    }

    // Custom FormData mapping example
    public static FrontendDemoExampleFormData mapMultipartParserResultToFrontendDemoExampleFormData(Map<String, List<FileItem>> parsedData) {
        String userName = null;
        String description = null;
        List<FileData> files = new ArrayList<>();

        for (Map.Entry<String, List<FileItem>> entry : parsedData.entrySet()) {
            String name = entry.getKey();
            List<FileItem> fileItems = entry.getValue();

            if (fileItems.isEmpty()) {
                continue;
            }

            FileItem item = fileItems.get(0);

            if (item.isFormField()) {
                // Text input
                String value = item.getString();
                switch (name) {
                    case "userName":
                        userName = value;
                        break;
                    case "description":
                        description = value;
                        break;
                }
            } else {
                // process File input with name "files" only
                if (!name.equals("files")) {
                    continue;
                }
                // File input
                for (FileItem fileItem : fileItems) {
                    files.add(new FileData(fileItem.getName(), fileItem.getContentType(), fileItem.get()));
                }
            }
        }
        return new FrontendDemoExampleFormData(userName, description, files);
    }
}