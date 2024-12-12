package com.demodaggerformdatafileupload.dto.formdata;

import com.demodaggerformdatafileupload.dto.FileData;

import java.util.List;
import java.util.Map;

/**
 * This class represents HTML FormData object with fields and files as a separated maps collections.
 */
public record FormDataV2(
        // Fields are stored as a map of field name to field value. (all input types except "file")
        Map<String, String> fields,
        // Files are stored as a list of FileData objects grouped by field name. (input type="file")
        Map<String, List<FileData>> files
) {
    public Map<String, String> getFields() {
        return fields;
    }

    public Map<String, List<FileData>> getFiles() {
        return files;
    }

}
