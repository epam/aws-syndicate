package com.demodaggerformdatafileupload.dto.formdata.input;

public abstract class Input {

    protected InputType inputType;
    protected String name;

    protected Input(InputType inputType, String name) {
        this.inputType = inputType;
        this.name = name;
    }

    public InputType getInputType() {
        return inputType;
    }

    public String getName() {
        return name;
    }

    abstract Object getValue();

}
