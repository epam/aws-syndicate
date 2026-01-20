package com.demodaggerformdatafileupload.dto;

import com.demodaggerformdatafileupload.dto.FileData;
import java.util.List;

public class FrontendDemoExampleFormData {
    private String userName;
    private String description;
    private List<FileData> files;

    public FrontendDemoExampleFormData(String userName, String description, List<FileData> files) {
        this.userName = userName;
        this.description = description;
        this.files = files;
    }

    public String getUserName() {
        return userName;
    }

    public String getDescription() {
        return description;
    }

    public List<FileData> getFiles() {
        return files;
    }
}