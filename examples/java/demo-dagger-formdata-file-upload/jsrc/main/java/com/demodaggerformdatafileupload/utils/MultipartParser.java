package com.demodaggerformdatafileupload.utils;

import com.demodaggerformdatafileupload.exception.ProcessFormDataException;
import org.apache.commons.fileupload.FileItem;

import java.util.List;
import java.util.Map;

public interface MultipartParser {

    Map<String, List<FileItem>> parse(String requestBody, String contentType) throws ProcessFormDataException;
}
