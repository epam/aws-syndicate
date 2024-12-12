package com.demodaggerformdatafileupload.dto.formdata.input;

public class TextInput extends Input {

    String value;

    public TextInput(String name, String value) {
        super(InputType.TEXT, name);
        this.value = value;
    }

    @Override
    public String getValue() {
        return value;
    }

}
