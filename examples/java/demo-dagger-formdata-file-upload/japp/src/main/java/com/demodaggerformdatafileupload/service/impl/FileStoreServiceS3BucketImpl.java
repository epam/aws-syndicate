package com.demodaggerformdatafileupload.service.impl;

import com.demodaggerformdatafileupload.dto.FileData;
import com.demodaggerformdatafileupload.service.FileStoreService;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetUrlRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import java.util.List;
import java.util.Map;

public class FileStoreServiceS3BucketImpl implements FileStoreService {

    private final String storageBucketName = System.getenv("STORAGE_BUCKET_NAME");
    private final String region = System.getenv("REGION");
    private final S3Client s3Client = S3Client.builder().region(Region.of(region)).build();

    @Override
    public String upload(FileData fileData, Map<String, String> metadata) {

        PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                .bucket(storageBucketName)
                .metadata(metadata)
                .key(fileData.getFilename())
                .contentType(fileData.getContentType())
                .build();

        s3Client.putObject(putObjectRequest, RequestBody.fromBytes(fileData.getContent()));

        return getFileUrl(fileData.getFilename());
    }

    @Override
    public List<String> getAll() {
        return s3Client.listObjectsV2Paginator(builder -> builder.bucket(storageBucketName))
                .contents().stream()
                .map(object -> getFileUrl(object.key()))
                .toList();
    }

    private String getFileUrl(String filename) {
        GetUrlRequest request = GetUrlRequest.builder()
                .bucket(storageBucketName)
                .key(filename)
                .build();

        return s3Client.utilities().getUrl(request).toString();
    }

}
