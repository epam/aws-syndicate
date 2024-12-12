package com.demodaggerformdatafileupload.handler;

import com.demodaggerformdatafileupload.handler.impl.GeneralHandler;
import com.demodaggerformdatafileupload.handler.impl.GetFilesHandler;
import com.demodaggerformdatafileupload.handler.impl.NotFoundHandler;
import com.demodaggerformdatafileupload.handler.impl.PostFilesHandler;
import com.demodaggerformdatafileupload.service.FileStoreService;
import com.demodaggerformdatafileupload.utils.MultipartParser;
import com.google.gson.Gson;
import dagger.Module;
import dagger.Provides;
import dagger.multibindings.IntoMap;
import dagger.multibindings.StringKey;

import javax.inject.Named;
import javax.inject.Singleton;
import java.util.Map;

/**
 * Module that provides handlers for the Dagger dependency injection framework
 */
@Module
public class HandlersModule {

    // General handler that routes requests to the appropriate handler based on the HTTP method and path
    @Singleton
    @Provides
    @Named("general")
    public EndpointHandler provideGeneralHandler(
            @Named("notFound") EndpointHandler notFoundHandler,
            Map<String, EndpointHandler> handlerMap) {
        return new GeneralHandler(notFoundHandler, handlerMap);
    }

    // Handler for 404 Not Found responses
    @Singleton
    @Provides
    @Named("notFound")
    public EndpointHandler provideNotFoundHandler(Gson gson) {
        return new NotFoundHandler(gson);
    }

    // Custom handlers for the API, grouped by HTTP method and path in the format "METHOD:path" into the map
    @Singleton
    @Provides
    @IntoMap
    @StringKey("POST:/files")
    public EndpointHandler providePutFilesHandler(FileStoreService fileStoreService, MultipartParser multipartParser, Gson gson) {
        return new PostFilesHandler(fileStoreService, multipartParser, gson);
    }

    @Singleton
    @Provides
    @IntoMap
    @StringKey("GET:/fileHs")
    public EndpointHandler provideGetFilesHandler(FileStoreService fileStoreService, Gson gson) {
        return new GetFilesHandler(fileStoreService, gson);
    }

}
