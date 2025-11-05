package com.example.customsdk;

import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.classic.HttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.EntityUtils;

public class RestServiceClient {
    private final HttpClient httpClient = HttpClients.createDefault();

    public String getFromUrl(String url) throws Exception {
        HttpGet request = new HttpGet(url);
        return httpClient.execute(request, response -> EntityUtils.toString(response.getEntity()));
    }
}

