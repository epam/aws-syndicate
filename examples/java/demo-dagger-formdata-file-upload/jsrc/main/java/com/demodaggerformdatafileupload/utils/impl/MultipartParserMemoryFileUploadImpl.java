package com.demodaggerformdatafileupload.utils.impl;

import com.demodaggerformdatafileupload.exception.ProcessFormDataException;
import com.demodaggerformdatafileupload.utils.MultipartParser;
import org.apache.commons.codec.binary.Base64;
import org.apache.commons.fileupload.FileItem;
import org.apache.commons.fileupload.FileItemFactory;
import org.apache.commons.fileupload.FileItemHeaders;
import org.apache.commons.fileupload.FileUpload;
import org.apache.commons.fileupload.FileUploadException;
import org.apache.commons.fileupload.ParameterParser;
import org.apache.commons.fileupload.UploadContext;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * This class is an implementation of the FormDataParser interface.
 * It uses the Apache Commons FileUpload library to parse the request body.
 * The request body is expected to be Base64 encoded,
 * for this, the "multipart/form-data" should be specified as the binary media type in the API Gateway settings.
 * Has 3 inner service classes: SimpleContext, MemoryFileItem, MemoryFileItemFactory.
 */
public class MultipartParserMemoryFileUploadImpl implements MultipartParser {

    @Override
    public Map<String, List<FileItem>> parse(String requestBody, String contentType) throws ProcessFormDataException {
        try {
            // check if the request body is Base64 encoded
            if (!Base64.isBase64(requestBody.getBytes())) {
                throw new ProcessFormDataException("Request body is not Base64 encoded");
            }
            // parse the request body, and fill the fields map and the files list with the parsed data
            return new FileUpload(new MemoryFileItemFactory())
                    .parseParameterMap(new SimpleContext(Base64.decodeBase64(requestBody), contentType));
        } catch (
                FileUploadException e) {
            throw new ProcessFormDataException("Failed to parse the request body. Reason: " + e.getMessage());
        }
    }

    /**
     * This inner class is a simple implementation of the UploadContext interface
     */
    private static class SimpleContext implements UploadContext {
        private final byte[] requestBody;
        private final String contentType;

        private SimpleContext(byte[] requestBody, String contentTypeHeader) {
            this.requestBody = requestBody;
            this.contentType = contentTypeHeader;
        }

        @Override
        public long contentLength() {
            return requestBody.length;
        }

        /**
         * The 'Content-Type' header may look like: multipart/form-data; charset=UTF-8; boundary="xxxx"
         * in which case we can extract the charset, otherwise, just default to UTF-8.
         */
        @Override
        public String getCharacterEncoding() {
            ParameterParser parser = new ParameterParser();
            parser.setLowerCaseNames(true);
            String charset = parser.parse(contentType, ';').get("charset");
            return charset != null ? charset : "UTF-8";
        }

        @Override
        public int getContentLength() {
            return requestBody.length;
        }

        @Override
        public String getContentType() {
            return contentType;
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return new ByteArrayInputStream(requestBody);
        }
    }

    /**
     * This inner class is a simple implementation of the FileItem interface.
     * A form field which stores the field or file data completely in memory.
     * Will be limited by the maximum size of a byte array (about 2GB).
     */
    private static class MemoryFileItem implements FileItem {
        private String fieldName;
        private final String fileName;
        private final String contentType;
        private boolean isFormField;
        private FileItemHeaders headers;
        private final ByteArrayOutputStream os = new ByteArrayOutputStream();

        public MemoryFileItem(String fieldName, String contentType, boolean isFormField, String fileName) {
            this.fieldName = fieldName;
            this.contentType = contentType;
            this.isFormField = isFormField;
            this.fileName = fileName;
        }

        @Override
        public void delete() {
            // Not implemented, because the data is stored in memory
        }

        @Override
        public byte[] get() {
            return os.toByteArray();
        }

        @Override
        public String getContentType() {
            return contentType;
        }

        @Override
        public String getFieldName() {
            return fieldName;
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return new ByteArrayInputStream(get());
        }

        @Override
        public String getName() {
            return fileName;
        }

        @Override
        public OutputStream getOutputStream() throws IOException {
            return os;
        }

        @Override
        public long getSize() {
            return os.size();
        }

        @Override
        public String getString() {
            return new String(get(), StandardCharsets.UTF_8);
        }

        @Override
        public String getString(String encoding) throws UnsupportedEncodingException {
            return new String(get(), encoding);
        }

        @Override
        public boolean isFormField() {
            return isFormField;
        }

        @Override
        public boolean isInMemory() {
            return true;
        }

        @Override
        public void setFieldName(String name) {
            fieldName = name;
        }

        @Override
        public void setFormField(boolean state) {
            isFormField = state;
        }

        @Override
        public void write(File file) throws Exception {
            // Not implemented, because the data is stored in memory
        }

        @Override
        public FileItemHeaders getHeaders() {
            return headers;
        }

        @Override
        public void setHeaders(FileItemHeaders headers) {
            this.headers = headers;
        }

    }

    /**
     * This inner  class is a simple implementation of the FileItemFactory interface
     */
    private static class MemoryFileItemFactory implements FileItemFactory {
        @Override
        public FileItem createItem(String fieldName, String contentType, boolean isFormField, String fileName) {
            return new MemoryFileItem(fieldName, contentType, isFormField, fileName);
        }
    }

}
