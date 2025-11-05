package com.demodaggerformdatafileupload.service;

import com.demodaggerformdatafileupload.service.impl.FileStoreServiceS3BucketImpl;
import dagger.Module;
import dagger.Provides;

import javax.inject.Singleton;

/**
 * Module that provides services for the Dagger dependency injection.
 */
@Module
public class ServicesModule {

    @Singleton
    @Provides
    FileStoreService provideFileService() {
        return new FileStoreServiceS3BucketImpl();
    }
}
