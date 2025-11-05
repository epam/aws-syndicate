package com.demodaggerformdatafileupload.dto.formdata;

import com.demodaggerformdatafileupload.dto.formdata.input.Input;

import java.util.Collection;

/**
 * This class represents HTML FormData object with inputs as a collection of Input objects.
 */
public record FormDataV1(
        Collection<Input> inputs
) {
    public Collection<Input> getInputs() {
        return inputs;
    }

}
