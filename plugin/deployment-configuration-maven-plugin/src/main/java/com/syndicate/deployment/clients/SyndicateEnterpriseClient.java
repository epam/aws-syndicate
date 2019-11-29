package com.syndicate.deployment.clients;

import com.syndicate.deployment.model.api.request.SyndicateCredentials;
import com.syndicate.deployment.model.api.request.SaveMetaRequest;
import com.syndicate.deployment.model.api.response.SaveMetaResponse;
import com.syndicate.deployment.model.api.response.TokenResponse;
import feign.Headers;
import feign.Param;
import feign.RequestLine;

/**
 * Created by Vladyslav Tereshchenko on 2/8/2019.
 */
public interface SyndicateEnterpriseClient {

    @RequestLine("POST /token")
    @Headers("Content-Type: application/json")
    TokenResponse token(SyndicateCredentials credentials);

    @RequestLine("POST /meta")
    @Headers({"Content-Type: application/json", "Authorization: {token}"})
    SaveMetaResponse saveMeta(@Param("token") String token, SaveMetaRequest saveMetaRequest);

}
