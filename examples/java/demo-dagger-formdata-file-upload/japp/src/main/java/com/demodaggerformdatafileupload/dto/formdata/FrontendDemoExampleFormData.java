package com.demodaggerformdatafileupload.dto.formdata;

import com.demodaggerformdatafileupload.dto.FileData;

import java.util.List;

public record FrontendDemoExampleFormData(
        String userName,
        String description,
        List<FileData> files
) {
}
