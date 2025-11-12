package com.demodaggerformdatafileupload.dto.formdata.input;

import com.demodaggerformdatafileupload.dto.FileData;

import java.util.List;

public class FileInput extends Input {

    private final List<FileData> value;

    public FileInput(String name, List<FileData> value) {
        super(InputType.FILE, name);
        this.value = value;
    }

    @Override
    public List<FileData> getValue() {
        return value;
    }

}
