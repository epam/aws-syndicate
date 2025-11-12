package com.demodaggerformdatafileupload;

import com.demodaggerformdatafileupload.handler.EndpointHandler;
import com.demodaggerformdatafileupload.handler.HandlersModule;
import com.demodaggerformdatafileupload.service.ServicesModule;
import com.demodaggerformdatafileupload.utils.UtilsModule;
import dagger.Component;

import javax.inject.Named;
import javax.inject.Singleton;
import java.util.Map;

/**
 * Application component. Assembly of all modules for the Dagger dependency injection framework.
 * Provides the general API handler and CORS headers.
 */
@Singleton
@Component(modules = {HandlersModule.class, ServicesModule.class, UtilsModule.class})
public interface Application {

    @Named("general")
    EndpointHandler getGeneralApiHandler();

    @Named("cors")
    Map<String, String> getCorsHeaders();
}
