package com.demodaggerformdatafileupload.service;

import com.demodaggerformdatafileupload.dto.FileData;

import java.util.List;
import java.util.Map;

public interface FileStoreService {

    // returns the URL of the uploaded file
    String upload(FileData fileData, Map<String, String> metadata);

    // returns the URLs of all fileUrls
    List<String> getAll();
}
