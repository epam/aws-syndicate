package com.syndicate.deployment.model.api.request;

/**
 * Created by Vladyslav Tereshchenko on 2/8/2019.
 */
public class SyndicateCredentials {

    private String email;

    private String password;

    public SyndicateCredentials(String email, String password) {
        this.email = email;
        this.password = password;
    }

    public String getEmail() {
        return email;
    }

    public String getPassword() {
        return password;
    }
}
