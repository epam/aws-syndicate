package com.demodaggerformdatafileupload.dto;

/**
 * Represents a file that is uploaded to the server.
 */
public record FileData(
        String filename,
        String contentType,
        byte[] content
) {

    public String getFilename() {
        return filename;
    }

    public String getContentType() {
        return contentType;
    }

    public byte[] getContent() {
        return content;
    }
}
