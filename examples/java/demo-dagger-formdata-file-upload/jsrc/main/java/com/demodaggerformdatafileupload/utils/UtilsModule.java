package com.demodaggerformdatafileupload.utils;

import com.demodaggerformdatafileupload.utils.impl.MultipartParserMemoryFileUploadImpl;
import com.google.gson.Gson;
import dagger.Module;
import dagger.Provides;

import javax.inject.Named;
import javax.inject.Singleton;
import java.util.Map;

/**
 * Module that provides utilities for the Dagger dependency injection framework.
 */
@Module
public class UtilsModule {

    @Singleton
    @Provides
    Gson provideGson() {
        return new Gson();
    }

    @Singleton
    @Provides
    MultipartParser provideFormDataParser() {
        return new MultipartParserMemoryFileUploadImpl();
    }

    @Singleton
    @Provides
    @Named("cors")
    Map<String, String> provideCorsHeaders() {
        return Map.of(
                "Access-Control-Allow-Headers", "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Origin", "*",
                "Access-Control-Allow-Methods", "*",
                "Accept-Version", "*"
        );
    }
}
