package com.demodaggerformdatafileupload.dto;

import java.util.List;

/**
 * DTO for file response
 */
public record FileResponse(
        List<String> fileUrls
) {
}
